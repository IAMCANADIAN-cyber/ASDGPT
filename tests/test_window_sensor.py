import unittest
from unittest.mock import MagicMock, patch
import sys
import platform
from sensors.window_sensor import WindowSensor

class TestWindowSensor(unittest.TestCase):

    def setUp(self):
        self.mock_logger = MagicMock()

    @patch('platform.system')
    def test_unknown_os(self, mock_system):
        mock_system.return_value = 'TempleOS'
        sensor = WindowSensor(self.mock_logger)
        self.assertEqual(sensor.get_active_window(), "Unknown")

    @patch('platform.system')
    @patch('ctypes.windll', create=True)
    @patch('ctypes.create_unicode_buffer')
    def test_windows_success(self, mock_create_buffer, mock_windll, mock_system):
        mock_system.return_value = 'Windows'

        # Setup mock user32
        mock_user32 = MagicMock()
        mock_windll.user32 = mock_user32

        # Mock GetForegroundWindow to return a handle
        mock_user32.GetForegroundWindow.return_value = 12345

        # Mock GetWindowTextLengthW to return length
        mock_user32.GetWindowTextLengthW.return_value = 10

        # Mock buffer
        mock_buffer_instance = MagicMock()
        mock_buffer_instance.value = "Notepad - Test"
        mock_create_buffer.return_value = mock_buffer_instance

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window()

        self.assertEqual(title, "Notepad - Test")
        mock_user32.GetForegroundWindow.assert_called_once()
        mock_user32.GetWindowTextW.assert_called_once()

    @patch('platform.system')
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_linux_missing_xprop(self, mock_subprocess, mock_which, mock_system):
        mock_system.return_value = 'Linux'
        mock_which.return_value = None # xprop not found

        sensor = WindowSensor(self.mock_logger)

        # Verify warning logged (prefer log_warning if available, which MagicMock is)
        self.mock_logger.log_warning.assert_called_with(
            "WindowSensor: 'xprop' utility not found. Active window detection will be unavailable. (Hint: install x11-utils)"
        )

        # Verify result is unknown
        self.assertEqual(sensor.get_active_window(), "Unknown")

        # Verify subprocess.run is NOT called (safe execution)
        mock_subprocess.assert_not_called()

    @patch('platform.system')
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_linux_success(self, mock_which, mock_subprocess, mock_system):
        mock_system.return_value = 'Linux'
        mock_which.return_value = '/usr/bin/xprop'

        # Mock sequence of calls
        # 1. xprop -root _NET_ACTIVE_WINDOW
        # 2. xprop -id <id> WM_NAME

        mock_res_root = MagicMock()
        mock_res_root.returncode = 0
        mock_res_root.stdout = "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x12345"

        mock_res_name = MagicMock()
        mock_res_name.returncode = 0
        mock_res_name.stdout = 'WM_NAME(STRING) = "Firefox - Reddit"'

        mock_subprocess.side_effect = [mock_res_root, mock_res_name]

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window()

        self.assertEqual(title, "Firefox - Reddit")
        self.assertEqual(mock_subprocess.call_count, 2)

    @patch('platform.system')
    @patch('subprocess.run')
    def test_macos_success(self, mock_subprocess, mock_system):
        mock_system.return_value = 'Darwin'

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "Safari"

        mock_subprocess.return_value = mock_res

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window()

        self.assertEqual(title, "Safari")

    def test_sanitization(self):
        # We don't need to patch OS for this if we test the private method or ensure it passes through
        # But let's test via public API by forcing the internal method return via mock?
        # Easier to just test the private method or patch the internal fetcher.

        sensor = WindowSensor(self.mock_logger)

        # Direct test of sanitizer
        self.assertEqual(sensor._sanitize_title("Hello World"), "Hello World")

        # Email
        self.assertEqual(sensor._sanitize_title("Contact alice@example.com now"), "Contact [EMAIL_REDACTED] now")

        # Windows Path
        self.assertEqual(sensor._sanitize_title("Editing C:\\Users\\Alice\\Documents\\report.txt"), "Editing [PATH_REDACTED]")

        # Linux Path
        self.assertEqual(sensor._sanitize_title("vim /home/alice/projects/code.py"), "vim [PATH_REDACTED]")

        # Mixed
        self.assertEqual(sensor._sanitize_title("Unknown"), "Unknown")
        self.assertEqual(sensor._sanitize_title(None), "Unknown")

    def test_sensitive_app_redaction(self):
        sensor = WindowSensor(self.mock_logger)

        # Patch config.SENSITIVE_APP_KEYWORDS
        test_keywords = ["SecretApp", "Incognito"]
        with patch('sensors.window_sensor.config.SENSITIVE_APP_KEYWORDS', test_keywords):
            # Test exact match
            self.assertEqual(sensor._sanitize_title("SecretApp"), "[REDACTED]")

            # Test partial match
            self.assertEqual(sensor._sanitize_title("Using SecretApp for work"), "[REDACTED]")

            # Test case insensitivity
            self.assertEqual(sensor._sanitize_title("secretapp running"), "[REDACTED]")

            # Test second keyword
            self.assertEqual(sensor._sanitize_title("Chrome Incognito"), "[REDACTED]")

            # Test no match
            self.assertEqual(sensor._sanitize_title("Normal App"), "Normal App")

    def test_default_config_keywords(self):
        """Verify that the default configuration correctly redacts standard sensitive apps."""
        sensor = WindowSensor(self.mock_logger)

        # Test known sensitive keywords (including new additions)
        sensitive_titles = [
            "KeePassXC - Database.kdbx",
            "Bitwarden - My Vault",
            "1Password - Login",
            "Private Browsing - Firefox",
            "Incognito Tab - Google Chrome",
            "Tor Browser",
            "LastPass",
            "My Secret Vault",
            "My Bank - Account Summary",
            "Login to Google",
            "User Authentication",
            "My Profile Settings"
        ]

        for title in sensitive_titles:
            sanitized = sensor._sanitize_title(title)
            self.assertEqual(sanitized, "[REDACTED]", f"Failed to redact: {title}")

        # Test safe titles
        safe_titles = [
            "Visual Studio Code",
            "My Project - Python",
            "Google Chrome - Search",
            "Notepad"
        ]
        for title in safe_titles:
            self.assertNotEqual(sensor._sanitize_title(title), "[REDACTED_SENSITIVE_APP]", f"Incorrectly redacted: {title}")

    def test_improved_email_redaction(self):
        sensor = WindowSensor(self.mock_logger)

        # Standard
        self.assertEqual(sensor._sanitize_title("alice@example.com"), "[EMAIL_REDACTED]")

        # Subdomain + Country TLD
        self.assertEqual(sensor._sanitize_title("bob.smith@corp.example.co.uk"), "[EMAIL_REDACTED]")

        # Within text
        self.assertEqual(sensor._sanitize_title("Compose to alice@example.com - Mail"), "Compose to [EMAIL_REDACTED] - Mail")

if __name__ == '__main__':
    unittest.main()
