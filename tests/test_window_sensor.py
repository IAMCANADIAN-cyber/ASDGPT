import unittest
from unittest.mock import MagicMock, patch
import sys
# Ensure we can import the sensor
from sensors.window_sensor import WindowSensor

class TestWindowSensor(unittest.TestCase):
    def setUp(self):
        self.sensor = WindowSensor()

    def test_sanitize_title(self):
        self.assertEqual(self.sensor._sanitize_title("Meeting with user@example.com"), "Meeting with [REDACTED]")
        self.assertEqual(self.sensor._sanitize_title("No email here"), "No email here")
        self.assertEqual(self.sensor._sanitize_title(""), "")
        self.assertEqual(self.sensor._sanitize_title("Contact support@test.co.uk now"), "Contact [REDACTED] now")

    @patch('sys.platform', 'linux')
    @patch('subprocess.check_output')
    def test_linux_detection_success(self, mock_subprocess):
        # Mock active window ID, Title, Class
        mock_subprocess.side_effect = [
            b'_NET_ACTIVE_WINDOW(WINDOW): window id # 0x12345',
            b'_NET_WM_NAME(UTF8_STRING) = "My App Title"',
            b'WM_CLASS(STRING) = "my_app", "My App"'
        ]

        info = self.sensor.get_active_window()
        self.assertEqual(info['title'], "My App Title")
        self.assertEqual(info['app_name'], "My App")

    @patch('sys.platform', 'linux')
    @patch('subprocess.check_output')
    def test_linux_detection_desktop(self, mock_subprocess):
        mock_subprocess.return_value = b'_NET_ACTIVE_WINDOW(WINDOW): window id # 0x0'
        info = self.sensor.get_active_window()
        self.assertEqual(info['title'], "Desktop")
        self.assertEqual(info['app_name'], "System")

    @patch('sys.platform', 'darwin')
    @patch('subprocess.check_output')
    def test_macos_detection(self, mock_subprocess):
        mock_subprocess.return_value = b"Safari, Google Search"

        info = self.sensor.get_active_window()
        self.assertEqual(info['app_name'], "Safari")
        self.assertEqual(info['title'], "Google Search")

    @patch('sys.platform', 'darwin')
    @patch('subprocess.check_output')
    def test_macos_detection_simple(self, mock_subprocess):
        # Test case where only app name is returned or comma missing
        mock_subprocess.return_value = b"Finder"

        info = self.sensor.get_active_window()
        self.assertEqual(info['app_name'], "Finder")
        self.assertEqual(info['title'], "")

    @patch('sys.platform', 'win32')
    def test_windows_detection(self):
        # Mocking ctypes for Windows test
        mock_ctypes = MagicMock()
        mock_user32 = mock_ctypes.windll.user32

        # Setup mock behavior
        mock_user32.GetForegroundWindow.return_value = 12345
        mock_user32.GetWindowTextLengthW.return_value = 13

        # Mock the buffer creation and value
        mock_buffer = MagicMock()
        mock_buffer.value = "Windows Title"
        mock_ctypes.create_unicode_buffer.return_value = mock_buffer

        # Inject the mock into sys.modules
        with patch.dict(sys.modules, {'ctypes': mock_ctypes}):
            info = self.sensor.get_active_window()
            self.assertEqual(info['title'], "Windows Title")
            self.assertEqual(info['app_name'], "Windows Application")

            # Verify calls
            mock_user32.GetForegroundWindow.assert_called_once()
            mock_user32.GetWindowTextW.assert_called_once()

    @patch('sys.platform', 'win32')
    def test_windows_detection_no_window(self):
        mock_ctypes = MagicMock()
        mock_user32 = mock_ctypes.windll.user32
        mock_user32.GetForegroundWindow.return_value = 0 # No active window

        with patch.dict(sys.modules, {'ctypes': mock_ctypes}):
            info = self.sensor.get_active_window()
            self.assertEqual(info['title'], "Unknown")

    @patch('sys.platform', 'unknown_os')
    def test_unknown_platform(self):
        info = self.sensor.get_active_window()
        self.assertEqual(info['title'], "Unknown")
        self.assertEqual(info['app_name'], "Unknown")

if __name__ == '__main__':
    unittest.main()
