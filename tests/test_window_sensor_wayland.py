import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure repo root is in path
sys.path.append(os.getcwd())

from sensors.window_sensor import WindowSensor
import config

class TestWindowSensorWayland(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.sensor = WindowSensor(self.mock_logger)
        # Force linux
        self.sensor.os_type = 'Linux'
        self.sensor.gdbus_available = True

    @patch('subprocess.run')
    @patch('os.environ.get')
    def test_gnome_wayland_success_quoted_double(self, mock_env, mock_run):
        # Setup Wayland environment
        mock_env.return_value = "wayland"

        # Mock gdbus response: (true, "My App")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '(true, "My App")'

        title = self.sensor._get_active_window_gnome_wayland()
        self.assertEqual(title, "My App")

    @patch('subprocess.run')
    @patch('os.environ.get')
    def test_gnome_wayland_success_quoted_single(self, mock_env, mock_run):
        mock_env.return_value = "wayland"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "(true, 'My App')"

        title = self.sensor._get_active_window_gnome_wayland()
        self.assertEqual(title, "My App")

    @patch('subprocess.run')
    def test_gnome_wayland_empty(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '(true, "")'

        title = self.sensor._get_active_window_gnome_wayland()
        self.assertEqual(title, "Unknown")

    @patch('subprocess.run')
    def test_gnome_wayland_failure(self, mock_run):
        mock_run.return_value.returncode = 1

        title = self.sensor._get_active_window_gnome_wayland()
        self.assertEqual(title, "Unknown")

    @patch('sensors.window_sensor.WindowSensor._get_active_window_gnome_wayland')
    @patch('os.environ.get')
    def test_get_active_window_priority(self, mock_env, mock_get_gnome):
        # Test that Wayland method is called first if session is wayland
        mock_env.return_value = "wayland"
        mock_get_gnome.return_value = "Wayland Window"

        title = self.sensor._get_active_window_linux()
        self.assertEqual(title, "Wayland Window")
        mock_get_gnome.assert_called_once()

    @patch('sensors.window_sensor.WindowSensor._get_active_window_gnome_wayland')
    @patch('os.environ.get')
    @patch('subprocess.run')
    def test_fallback_to_xprop(self, mock_run, mock_env, mock_get_gnome):
        # Test fallback if Wayland method fails
        mock_env.return_value = "wayland"
        mock_get_gnome.return_value = "Unknown"

        # Enable xprop
        self.sensor.xprop_available = True

        # Mock xprop responses
        # 1. -root -> id
        # 2. -id -> title
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="_NET_ACTIVE_WINDOW(WINDOW): window id # 0x12345"),
            MagicMock(returncode=0, stdout='_NET_WM_NAME(UTF8_STRING) = "X11 Window"')
        ]

        title = self.sensor._get_active_window_linux()
        self.assertEqual(title, "X11 Window")
        mock_get_gnome.assert_called_once()

if __name__ == '__main__':
    unittest.main()
