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
    @patch('subprocess.run')
    def test_linux_success(self, mock_subprocess, mock_system):
        mock_system.return_value = 'Linux'

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
    def test_linux_regex_parsing(self, mock_subprocess, mock_system):
        """Test robust parsing of xprop output with quotes."""
        mock_system.return_value = 'Linux'

        mock_res_root = MagicMock()
        mock_res_root.returncode = 0
        mock_res_root.stdout = "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x12345"

        mock_res_name = MagicMock()
        mock_res_name.returncode = 0
        # Simulating xprop output with escaped quotes
        # Actual xprop behavior varies but often escapes quotes
        mock_res_name.stdout = 'WM_NAME(STRING) = "Code - \\"hello.py\\" [Administrator]"'

        mock_subprocess.side_effect = [mock_res_root, mock_res_name]

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window()

        self.assertEqual(title, 'Code - \\"hello.py\\" [Administrator]')

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
        sensor = WindowSensor(self.mock_logger)

        # Direct test of sanitizer
        self.assertEqual(sensor._sanitize_title("Hello World"), "Hello World")

        # Email
        self.assertEqual(sensor._sanitize_title("Contact alice@example.com now"), "Contact [EMAIL_REDACTED] now")

        # Windows Path
        self.assertEqual(sensor._sanitize_title("Editing C:\\Users\\Alice\\Documents\\secret.txt"), "Editing [PATH_REDACTED]")

        # Linux Path
        self.assertEqual(sensor._sanitize_title("vim /home/alice/projects/code.py"), "vim [PATH_REDACTED]")

        # Mixed
        self.assertEqual(sensor._sanitize_title("Unknown"), "Unknown")
        self.assertEqual(sensor._sanitize_title(None), "Unknown")

    def test_sensitive_app_redaction(self):
        sensor = WindowSensor(self.mock_logger)

        # Patch config on the module where it is imported
        with patch('sensors.window_sensor.config') as mock_config:
            mock_config.SENSITIVE_APP_KEYWORDS = ["vault", "bank", "1password"]

            # Should be redacted
            self.assertEqual(sensor._sanitize_title("My Vault - 1Password"), "[REDACTED_SENSITIVE_APP]")
            self.assertEqual(sensor._sanitize_title("Chase Bank Login"), "[REDACTED_SENSITIVE_APP]")

            # Should NOT be redacted
            self.assertEqual(sensor._sanitize_title("VS Code"), "VS Code")

            # Case insensitive check
            self.assertEqual(sensor._sanitize_title("MY VAULT"), "[REDACTED_SENSITIVE_APP]")

if __name__ == '__main__':
    unittest.main()
