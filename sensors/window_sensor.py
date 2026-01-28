import sys
import subprocess
import re
import logging
from typing import Dict

class WindowSensor:
    def __init__(self):
        self.logger = logging.getLogger("ACR.WindowSensor")
        self.logger.info("WindowSensor initialized.")

    def get_active_window(self) -> Dict[str, str]:
        platform = sys.platform
        window_info = {"title": "Unknown", "app_name": "Unknown"}

        try:
            if platform == "win32":
                window_info = self._get_window_win32()
            elif platform == "darwin":
                window_info = self._get_window_darwin()
            elif platform.startswith("linux"):
                window_info = self._get_window_linux()
        except Exception as e:
            # Common to fail if tools aren't installed or permissions denied
            # Log debug to avoid spamming logs every second if it fails
            self.logger.debug(f"Failed to get active window: {e}")

        window_info["title"] = self._sanitize_title(window_info.get("title", ""))
        return window_info

    def _get_window_win32(self) -> Dict[str, str]:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return {"title": "Unknown", "app_name": "Windows"}

            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
            else:
                title = "Unknown"

            return {"title": title, "app_name": "Windows Application"}
        except ImportError:
            return {"title": "Error (ctypes missing)", "app_name": "Windows"}

    def _get_window_darwin(self) -> Dict[str, str]:
        # AppleScript to get frontmost app and window title
        # Returns string: "AppName, WindowTitle"
        script = 'tell application "System Events" to get {name, (value of attribute "AXTitle" of window 1)} of (first application process whose frontmost is true)'
        cmd = ['osascript', '-e', script]

        # Run with timeout to prevent hanging
        result = subprocess.check_output(cmd, timeout=1).decode('utf-8').strip()

        # Result is typically "AppName, WindowTitle" but complex if title has commas
        # Simple split is risky, but good enough for MVP.
        # Better: use separate calls or specific delimiter.
        # Let's try to handle basic comma separation provided by default AppleScript string coercion
        parts = result.split(', ', 1)
        app_name = parts[0]
        title = parts[1] if len(parts) > 1 else ""

        return {"app_name": app_name, "title": title}

    def _get_window_linux(self) -> Dict[str, str]:
        # Using xprop
        # Check active window ID
        root = subprocess.check_output(['xprop', '-root', '_NET_ACTIVE_WINDOW'], stderr=subprocess.DEVNULL).decode('utf-8')

        # Format: "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x12345"
        try:
            window_id = root.split()[-1]
        except IndexError:
             return {"title": "Unknown", "app_name": "Linux"}

        if window_id == "0x0" or "no such" in window_id.lower():
            return {"title": "Desktop", "app_name": "System"}

        # Get Title
        title = "Unknown"
        try:
            title_output = subprocess.check_output(['xprop', '-id', window_id, '_NET_WM_NAME'], stderr=subprocess.DEVNULL).decode('utf-8')
            # Format: "_NET_WM_NAME(UTF8_STRING) = \"Title\""
            if " = " in title_output:
                title = title_output.split(' = ')[1].strip('" \n')
        except subprocess.CalledProcessError:
            pass

        # Get App Name (WM_CLASS)
        app_name = "Linux Application"
        try:
            class_output = subprocess.check_output(['xprop', '-id', window_id, 'WM_CLASS'], stderr=subprocess.DEVNULL).decode('utf-8')
            # Format: "WM_CLASS(STRING) = \"res_name\", \"res_class\""
            if " = " in class_output:
                parts = class_output.split(' = ')[1].split(',')
                if len(parts) > 1:
                    app_name = parts[1].strip('" \n')
                elif len(parts) > 0:
                     app_name = parts[0].strip('" \n')
        except subprocess.CalledProcessError:
            pass

        return {"title": title, "app_name": app_name}

    def _sanitize_title(self, title: str) -> str:
        if not title: return ""
        # Regex for email-like patterns (simple version)
        # Identifies string@string.domain
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.sub(email_regex, '[REDACTED]', title)
