import unittest
from unittest.mock import MagicMock, patch
import sys
import platform
from sensors.window_sensor import WindowSensor

class TestWindowSensor(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.sensor = WindowSensor(logger=self.mock_logger)

    def test_initialization(self):
        self.assertIsNotNone(self.sensor)
        self.assertEqual(self.sensor.logger, self.mock_logger)

    @patch('platform.system')
    def test_get_active_window_windows(self, mock_system):
        mock_system.return_value = "Windows"
        # Re-initialize to pick up the mocked system if needed,
        # but the class stores self.system in __init__.
        # So we need to patch platform.system BEFORE init or manually set self.system
        sensor = WindowSensor(logger=self.mock_logger)

        with patch('ctypes.windll', create=True) as mock_windll:
            mock_user32 = MagicMock()
            mock_windll.user32 = mock_user32

            # Mock GetWindowTextW behavior
            def side_effect(hwnd, buff, length):
                buff.value = "Active Window Title"
                return length

            mock_user32.GetWindowTextW.side_effect = side_effect
            mock_user32.GetWindowTextLengthW.return_value = 20

            result = sensor.get_active_window()
            self.assertEqual(result['title'], "Active Window Title")

    @patch('platform.system')
    def test_get_active_window_linux(self, mock_system):
        mock_system.return_value = "Linux"
        sensor = WindowSensor(logger=self.mock_logger)

        with patch('subprocess.check_output') as mock_subprocess:
            # Mock xprop output
            # First call: get ID
            # Second call: get Title
            mock_subprocess.side_effect = [
                b"_NET_ACTIVE_WINDOW(WINDOW): window id # 0x12345",
                b'_NET_WM_NAME(UTF8_STRING) = "Linux Window Title"'
            ]

            result = sensor.get_active_window()
            self.assertEqual(result['title'], "Linux Window Title")

    @patch('platform.system')
    def test_get_active_window_macos(self, mock_system):
        mock_system.return_value = "Darwin"
        sensor = WindowSensor(logger=self.mock_logger)

        with patch('subprocess.check_output') as mock_subprocess:
            mock_subprocess.return_value = b"MacOS Window Title\n"

            result = sensor.get_active_window()
            self.assertEqual(result['title'], "MacOS Window Title")

    def test_sanitization(self):
        # We can test private method _sanitize_title directly or via get_active_window
        # Testing directly is easier for specific cases

        # 1. Email Redaction
        title = "Meeting with active.user@example.com regarding project"
        sanitized = self.sensor._sanitize_title(title)
        self.assertEqual(sanitized, "Meeting with [REDACTED_EMAIL] regarding project")

        # 2. Multiple Emails
        title = "Email to bob@test.com and alice@test.co.uk"
        sanitized = self.sensor._sanitize_title(title)
        self.assertEqual(sanitized, "Email to [REDACTED_EMAIL] and [REDACTED_EMAIL]")

        # 3. No PII
        title = "Clean Title"
        sanitized = self.sensor._sanitize_title(title)
        self.assertEqual(sanitized, "Clean Title")

        # 4. Empty/None
        self.assertEqual(self.sensor._sanitize_title(""), "Unknown")
        self.assertEqual(self.sensor._sanitize_title(None), "Unknown")

    @patch('platform.system')
    def test_error_handling_linux_no_xprop(self, mock_system):
        mock_system.return_value = "Linux"
        sensor = WindowSensor(logger=self.mock_logger)

        with patch('subprocess.check_output') as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError("No such file or directory")

            result = sensor.get_active_window()
            self.assertEqual(result['title'], "Unknown (xprop missing)")

    @patch('platform.system')
    def test_error_handling_general(self, mock_system):
        # Test generic exception in main flow
        mock_system.return_value = "Windows"
        sensor = WindowSensor(logger=self.mock_logger)

        # Patch the internal method to raise exception
        sensor._get_window_title_windows = MagicMock(side_effect=Exception("General Failure"))

        result = sensor.get_active_window()
        self.assertEqual(result['title'], "Unknown")
        # Should log warning
        self.mock_logger.log_warning.assert_called()

if __name__ == '__main__':
    unittest.main()
