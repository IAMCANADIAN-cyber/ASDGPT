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
        self.sensor.qdbus_available = True
        self.sensor.qdbus_bin = "qdbus"

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

    @patch('subprocess.run')
    def test_kde_wayland_success(self, mock_run):
        # Mock qdbus output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = """
Windows:
  Window: 1
    caption: Other App
    active: false
  Window: 2
    caption: KDE App
    active: true
        """

        title = self.sensor._get_active_window_kwin_wayland()
        self.assertEqual(title, "KDE App")

        # Verify call arguments
        mock_run.assert_called_with(['qdbus', 'org.kde.KWin', '/KWin', 'supportInformation'], capture_output=True, text=True, timeout=1)

    @patch('subprocess.run')
    def test_kde_wayland_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        title = self.sensor._get_active_window_kwin_wayland()
        self.assertEqual(title, "Unknown")

    @patch('sensors.window_sensor.WindowSensor._get_active_window_kwin_wayland')
    @patch('sensors.window_sensor.WindowSensor._get_active_window_gnome_wayland')
    @patch('os.environ.get')
    def test_dispatch_gnome(self, mock_env, mock_gnome, mock_kwin):
        # Mock env
        def get_env(key, default=None):
            if key == "XDG_SESSION_TYPE": return "wayland"
            if key == "XDG_CURRENT_DESKTOP": return "ubuntu:GNOME"
            return default
        mock_env.side_effect = get_env

        mock_gnome.return_value = "Gnome Window"
        mock_kwin.return_value = "Unknown"

        title = self.sensor._get_active_window_linux()
        self.assertEqual(title, "Gnome Window")

        mock_gnome.assert_called_once()
        mock_kwin.assert_not_called()

    @patch('sensors.window_sensor.WindowSensor._get_active_window_kwin_wayland')
    @patch('sensors.window_sensor.WindowSensor._get_active_window_gnome_wayland')
    @patch('os.environ.get')
    def test_dispatch_kde(self, mock_env, mock_gnome, mock_kwin):
        # Mock env
        def get_env(key, default=None):
            if key == "XDG_SESSION_TYPE": return "wayland"
            if key == "XDG_CURRENT_DESKTOP": return "KDE"
            return default
        mock_env.side_effect = get_env

        mock_kwin.return_value = "KDE Window"
        mock_gnome.return_value = "Unknown"

        title = self.sensor._get_active_window_linux()
        self.assertEqual(title, "KDE Window")

        mock_kwin.assert_called_once()
        mock_gnome.assert_not_called()

    @patch('sensors.window_sensor.WindowSensor._get_active_window_kwin_wayland')
    @patch('sensors.window_sensor.WindowSensor._get_active_window_gnome_wayland')
    @patch('os.environ.get')
    def test_dispatch_fallback(self, mock_env, mock_gnome, mock_kwin):
        # Mock env - unknown desktop
        def get_env(key, default=None):
            if key == "XDG_SESSION_TYPE": return "wayland"
            if key == "XDG_CURRENT_DESKTOP": return ""
            return default
        mock_env.side_effect = get_env

        # Let's say KDE fails but GNOME succeeds (unlikely in reality but possible logic path)
        mock_kwin.return_value = "Unknown"
        mock_gnome.return_value = "Fallback Window"

        title = self.sensor._get_active_window_linux()
        self.assertEqual(title, "Fallback Window")

        # Verify both called
        mock_kwin.assert_called_once()
        mock_gnome.assert_called_once()

    @patch('sensors.window_sensor.WindowSensor._get_active_window_gnome_wayland')
    @patch('os.environ.get')
    @patch('subprocess.run')
    def test_fallback_to_xprop(self, mock_run, mock_env, mock_get_gnome):
        # Update mock behavior to handle multiple calls to os.environ.get
        def get_env(key, default=None):
            if key == "XDG_SESSION_TYPE": return "wayland"
            if key == "XDG_CURRENT_DESKTOP": return "GNOME"
            return default
        mock_env.side_effect = get_env

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
