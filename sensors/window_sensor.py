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

             # Check for gdbus (GNOME/GTK Wayland)
             if shutil.which("gdbus"):
                 self.gdbus_available = True
             else:
                 self.gdbus_available = False

             # Check for qdbus (KDE Plasma Wayland)
             if shutil.which("qdbus"):
                 self.qdbus_available = True
             elif shutil.which("qdbus-qt5"): # Fallback for some distros
                 self.qdbus_command = "qdbus-qt5"
                 self.qdbus_available = True
             else:
                 self.qdbus_available = False
                 self.qdbus_command = "qdbus" # Default

             # Check for Wayland
             session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
             if "wayland" in session_type:
                 self._log_debug("Wayland detected. Will prioritize Wayland-compatible detection methods.")

    def get_active_window(self, sanitize: bool = True) -> str:
        """
        Returns the title of the currently active window.
        Returns "Unknown" if detection fails or is unsupported.
        :param sanitize: If True, redaction rules are applied.
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

        if sanitize:
            return self._sanitize_title(title)
        return title

    def _get_active_window_gnome_wayland(self) -> str:
        """
        Attempts to get the active window title using gdbus on GNOME Shell (Wayland).
        Requires org.gnome.Shell.Eval or similar exposure.
        """
        if not self.gdbus_available:
            return "Unknown"

        try:
            # Command: gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.Eval 'global.display.focus_window ? global.display.focus_window.get_title() : ""'
            # Note: This is often restricted in newer GNOME versions (41+).
            cmd = [
                'gdbus', 'call',
                '--session',
                '--dest', 'org.gnome.Shell',
                '--object-path', '/org/gnome/Shell',
                '--method', 'org.gnome.Shell.Eval',
                'global.display.focus_window ? global.display.focus_window.get_title() : ""'
            ]

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
            if res.returncode == 0:
                # Output format is typically: (true, "Window Title")
                output = res.stdout.strip()
                # Parse the variant output
                # We expect (true, 'String') or (true, "String")
                if output.startswith("(true,"):
                    # Extract the string part. It might be quoted.
                    # Basic regex to grab content between quotes
                    match = re.search(r'^\(true,\s*(?:\'|")(.+)(?:\'|")\)$', output)
                    if match:
                        return match.group(1)

                    # Fallback for empty string or unquoted (unlikely for string return)
                    if '""' in output or "''" in output:
                        return "Unknown"
            else:
                 self._log_debug(f"GNOME Wayland call failed (Code {res.returncode}). Eval interface likely restricted.")

        except Exception as e:
            self._log_debug(f"GNOME Wayland detection failed: {e}")

        return "Unknown"

    def _get_active_window_kwin_wayland(self) -> str:
        """
        Attempts to get the active window title using qdbus on KDE Plasma (Wayland).
        """
        if not self.qdbus_available:
            return "Unknown"

        try:
            cmd_name = getattr(self, 'qdbus_command', 'qdbus')
            cmd = [cmd_name, 'org.kde.KWin', '/KWin', 'org.kde.KWin.activeWindow']

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
            if res.returncode == 0:
                output = res.stdout
                # KDE qdbus output for a map (a{sv}) typically looks like:
                # argument 0: a{sv} {
                #  "caption": [Variant(QString): "My Title"],
                #  ...
                # }

                # Regex to find "caption" key and extract value
                # Pattern looks for "caption": [Variant(QString): "VALUE"]
                # or simplified: "caption": ... "VALUE"
                match = re.search(r'"caption":\s*\[Variant\(QString\):\s*"(.*?)"\]', output)
                if match:
                    return match.group(1).replace('\\"', '"').replace('\\\\', '\\')

                # Fallback: maybe format is simpler in some versions?
                # "caption": "Value"
                match_simple = re.search(r'"caption":\s*"(.*?)"', output)
                if match_simple:
                    return match_simple.group(1).replace('\\"', '"').replace('\\\\', '\\')

        except Exception as e:
             self._log_debug(f"KDE Wayland detection failed: {e}")

        return "Unknown"

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
        # Check priority based on session type
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if "wayland" in session_type:
            # Check Desktop Environment priority
            desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()

            # KDE Plasma Wayland
            if "KDE" in desktop:
                title = self._get_active_window_kwin_wayland()
                if title and title != "Unknown":
                    return title

            # GNOME Wayland
            elif "GNOME" in desktop:
                title = self._get_active_window_gnome_wayland()
                if title and title != "Unknown":
                    return title

            # Generic/Fallback: Try available methods if DE is ambiguous
            else:
                # Try KDE first (cleaner interface if present)
                if self.qdbus_available:
                    title = self._get_active_window_kwin_wayland()
                    if title and title != "Unknown":
                        return title

                # Try GNOME
                if self.gdbus_available:
                    title = self._get_active_window_gnome_wayland()
                    if title and title != "Unknown":
                        return title

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

            # 2. Get title of that window (Prioritize _NET_WM_NAME for UTF-8 support)
            # Try _NET_WM_NAME first
            name_res = subprocess.run(
                ['xprop', '-id', window_id, '_NET_WM_NAME'],
                capture_output=True, text=True, timeout=1
            )

            output = ""
            if name_res.returncode == 0:
                output = name_res.stdout.strip()

            # Fallback to WM_NAME if _NET_WM_NAME is missing or empty
            if not output or "not found" in output.lower() or "=" not in output:
                name_res = subprocess.run(
                    ['xprop', '-id', window_id, 'WM_NAME'],
                    capture_output=True, text=True, timeout=1
                )
                if name_res.returncode == 0:
                    output = name_res.stdout.strip()

            if not output:
                return "Unknown"

            # Use robust regex to extract title inside quotes, handling escaped quotes
            # Pattern: matches ' = "' followed by any char (except " or \) OR an escaped char, ending with '"'
            match = re.search(r'=\s*"((?:[^"\\]|\\.)*)"', output)
            if match:
                raw_title = match.group(1)
                # Unescape xprop's output (basic unescape for \" and \\)
                try:
                    # Using codecs to decode unicode escapes if present, though xprop usually outputs literals
                    # For safety, just simple replacement for common escapes
                    title = raw_title.replace('\\"', '"').replace('\\\\', '\\')
                    return title
                except Exception:
                    return raw_title

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
            sensitive_keywords = config.SENSITIVE_APP_KEYWORDS
            if isinstance(sensitive_keywords, list):
                title_lower = title.lower()
                for keyword in sensitive_keywords:
                    if keyword.lower() in title_lower:
                        return "[REDACTED]"

        # 2. Redact Email Addresses
        # Improved regex for email (handles subdomains and common TLDs)
        title = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL_REDACTED]', title)

        # 3. Redact File Paths
        # Windows paths (e.g. C:\Users\...)
        title = re.sub(r'[a-zA-Z]:\\[\w\\\.\s-]+', '[PATH_REDACTED]', title)
        # Unix paths (e.g. /home/user/...) - Be careful not to match simple words, look for at least 2 levels
        title = re.sub(r'/(?:[\w\.-]+/){2,}[\w\.-]+', '[PATH_REDACTED]', title)

        return title.strip()
