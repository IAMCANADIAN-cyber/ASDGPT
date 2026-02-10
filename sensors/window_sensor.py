import platform
import subprocess
import re
import sys
import os
import shutil
import logging
from typing import Optional, Any, List
import config

class WindowSensor:
    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger
        self.os_type = platform.system()
        self.xprop_available = False
        self._setup_platform()

    def _log_warning(self, msg: str):
        if self.logger:
            if hasattr(self.logger, 'log_warning'):
                self.logger.log_warning(msg)
            elif hasattr(self.logger, 'warning'):
                self.logger.warning(msg)

    def _log_debug(self, msg: str):
        if self.logger:
            if hasattr(self.logger, 'log_debug'):
                self.logger.log_debug(msg)
            elif hasattr(self.logger, 'debug'):
                self.logger.debug(msg)

    def _setup_platform(self):
        if self.os_type == 'Windows':
            try:
                import ctypes
                self.user32 = ctypes.windll.user32
            except ImportError:
                self.user32 = None
                self._log_warning("ctypes not available on Windows. WindowSensor disabled.")
        elif self.os_type == 'Linux':
             # Check for xprop
             if shutil.which("xprop"):
                 self.xprop_available = True
             else:
                 self.xprop_available = False
                 self._log_warning("WindowSensor: 'xprop' utility not found. Active window detection will be unavailable. (Hint: install x11-utils)")

             # Check for Wayland
             session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
             if "wayland" in session_type:
                 self._log_warning("Wayland detected. 'xprop' based window detection may fail or return generic values.")

    def get_active_window(self) -> str:
        """
        Returns the sanitized title of the currently active window.
        Returns "Unknown" if detection fails or is unsupported.
        """
        title = "Unknown"
        try:
            if self.os_type == 'Windows':
                title = self._get_active_window_windows()
            elif self.os_type == 'Linux':
                title = self._get_active_window_linux()
            elif self.os_type == 'Darwin': # macOS
                title = self._get_active_window_macos()
        except Exception as e:
            self._log_debug(f"Error getting active window: {e}")

        return self._sanitize_title(title)

    def _get_active_window_windows(self) -> str:
        if not self.user32:
            return "Unknown"

        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return "Unknown"

        length = self.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            # Allocate buffer
            import ctypes
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        return "Unknown"

    def _get_active_window_linux(self) -> str:
        if not self.xprop_available:
            return "Unknown"

        # Try using xprop
        try:
            # 1. Get ID of active window
            root_res = subprocess.run(
                ['xprop', '-root', '_NET_ACTIVE_WINDOW'],
                capture_output=True, text=True, timeout=1
            )
            if root_res.returncode != 0:
                return "Unknown"

            # Output format: "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x440000a"
            # We want the id at the end
            parts = root_res.stdout.strip().split()
            if not parts:
                return "Unknown"

            window_id = parts[-1]

            # 2. Get title of that window
            name_res = subprocess.run(
                ['xprop', '-id', window_id, 'WM_NAME'],
                capture_output=True, text=True, timeout=1
            )
            if name_res.returncode != 0:
                return "Unknown"

            # Output: WM_NAME(STRING) = "Title"
            # or WM_NAME(UTF8_STRING) = "Title"
            output = name_res.stdout.strip()

            # Use regex to extract title inside quotes
            match = re.search(r'WM_NAME\(.*?\) = "(.*)"', output)
            if match:
                return match.group(1)

        except FileNotFoundError:
            # xprop not installed
            return "Unknown"
        except Exception:
            pass

        return "Unknown"

    def _get_active_window_macos(self) -> str:
        # AppleScript to get the name of the frontmost application's window
        script = 'tell application "System Events" to get name of window 1 of (first application process whose frontmost is true)'
        try:
            res = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=1
            )
            if res.returncode == 0:
                return res.stdout.strip()

            # Fallback: Just get the application name
            script_app = 'tell application "System Events" to get name of first application process whose frontmost is true'
            res_app = subprocess.run(
                ['osascript', '-e', script_app],
                capture_output=True, text=True, timeout=1
            )
            if res_app.returncode == 0:
                return res_app.stdout.strip()

        except FileNotFoundError:
            return "Unknown"
        except Exception:
            pass

        return "Unknown"

    def _sanitize_title(self, title: str) -> str:
        if not title or title == "Unknown":
            return "Unknown"

        # 1. Check for Sensitive Apps (Config list)
        if hasattr(config, 'SENSITIVE_APP_KEYWORDS'):
            title_lower = title.lower()
            for keyword in config.SENSITIVE_APP_KEYWORDS:
                if keyword.lower() in title_lower:
                    return "[REDACTED_SENSITIVE_APP]"

        # 2. Redact Email Addresses
        # Improved regex for email (handles subdomains and common TLDs)
        title = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL_REDACTED]', title)

        # 3. Redact File Paths
        # Windows paths (e.g. C:\Users\...)
        title = re.sub(r'[a-zA-Z]:\\[\w\\\.\s-]+', '[PATH_REDACTED]', title)
        # Unix paths (e.g. /home/user/...) - Be careful not to match simple words, look for at least 2 levels
        title = re.sub(r'/(?:[\w\.-]+/){2,}[\w\.-]+', '[PATH_REDACTED]', title)

        return title.strip()
