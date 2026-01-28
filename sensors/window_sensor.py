import platform
import subprocess
import sys
import re
import ctypes
from typing import Optional, Dict

class WindowSensor:
    def __init__(self, logger=None):
        self.logger = logger
        self.system = platform.system()

        # Pre-compile regex for PII sanitization
        # Detects email addresses
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

        if self.logger:
            self.logger.log_info(f"WindowSensor initialized on {self.system}.")

    def get_active_window(self) -> Dict[str, str]:
        """
        Returns a dictionary containing the active window title.
        Example: {'title': 'Project - VS Code'}
        """
        title = "Unknown"
        try:
            if self.system == "Windows":
                title = self._get_window_title_windows()
            elif self.system == "Linux":
                title = self._get_window_title_linux()
            elif self.system == "Darwin":
                title = self._get_window_title_macos()
        except Exception as e:
            if self.logger:
                self.logger.log_warning(f"Error getting active window: {e}")

        sanitized_title = self._sanitize_title(title)
        return {"title": sanitized_title}

    def _get_window_title_windows(self) -> str:
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                return buff.value
            return "Unknown"
        except Exception:
            return "Unknown"

    def _get_window_title_linux(self) -> str:
        # Try xprop (X11)
        try:
            # Get active window ID
            root_out = subprocess.check_output(['xprop', '-root', '_NET_ACTIVE_WINDOW'], stderr=subprocess.DEVNULL)
            # Output format: "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x440000a"
            match = re.search(r'0x[0-9a-fA-F]+', root_out.decode('utf-8'))
            if match:
                window_id = match.group(0)
                # Get window title
                title_out = subprocess.check_output(['xprop', '-id', window_id, '_NET_WM_NAME'], stderr=subprocess.DEVNULL)
                # Output format: "_NET_WM_NAME(UTF8_STRING) = \"Title\""
                title_match = re.search(r'"(.*)"', title_out.decode('utf-8'))
                if title_match:
                    return title_match.group(1)
            return "Unknown"
        except FileNotFoundError:
             # xprop might not be installed
             return "Unknown (xprop missing)"
        except Exception:
            return "Unknown"

    def _get_window_title_macos(self) -> str:
        try:
            # AppleScript to get the name of the window of the frontmost application
            script = 'tell application "System Events" to get name of window 1 of (first application process whose frontmost is true)'
            output = subprocess.check_output(['osascript', '-e', script], stderr=subprocess.DEVNULL)
            return output.decode('utf-8').strip()
        except Exception:
            try:
                # Fallback to just application name if window title fails
                script = 'tell application "System Events" to get name of first application process whose frontmost is true'
                output = subprocess.check_output(['osascript', '-e', script], stderr=subprocess.DEVNULL)
                return output.decode('utf-8').strip()
            except Exception:
                return "Unknown"

    def _sanitize_title(self, title: str) -> str:
        """
        Sanitizes the window title to remove sensitive information like PII.
        """
        if not title:
            return "Unknown"

        # Redact emails
        title = self.email_pattern.sub('[REDACTED_EMAIL]', title)

        # Future: Redact other PII patterns (phone numbers, IPs, etc.)

        return title.strip()
