import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from sensors.window_sensor import WindowSensor

class TestWindowSensorWayland(unittest.TestCase):

    def setUp(self):
        self.mock_logger = MagicMock()
        with patch('shutil.which', return_value='/usr/bin/qdbus'):
            self.sensor = WindowSensor(self.mock_logger)
        # Force linux
        self.sensor.os_type = 'Linux'
        self.sensor.gdbus_available = True
        self.sensor.qdbus_available = True
        self.sensor.qdbus_bin = "qdbus"

    @patch('platform.system')
    @patch('shutil.which')
    def test_setup_platform_kde(self, mock_which, mock_system):
        mock_system.return_value = 'Linux'
        # Simulate qdbus availability
        mock_which.side_effect = lambda x: '/usr/bin/qdbus' if x in ['qdbus', 'qdbus-qt5'] else None

        sensor = WindowSensor(self.mock_logger)
        self.assertTrue(getattr(sensor, 'qdbus_available', False))
        self.assertEqual(getattr(sensor, 'qdbus_bin'), 'qdbus')

    @patch('subprocess.run')
    def test_kde_wayland_success(self, mock_run):
        # Mock qdbus output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = """
KWin Support Information:
...
Active Window: Window(0x55d4e3a1b0 caption="Konsole — bash")
...
"""
        title = self.sensor._get_active_window_kwin_wayland()
        self.assertEqual(title, "Konsole — bash")

        # Verify call arguments
        mock_run.assert_called_with(['qdbus', 'org.kde.KWin', '/KWin', 'supportInformation'], capture_output=True, text=True, timeout=1)

    @patch('subprocess.run')
    def test_kde_wayland_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        title = self.sensor._get_active_window_kwin_wayland()
        self.assertEqual(title, "Unknown")

    @patch('subprocess.run')
    def test_gnome_wayland_success(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "(true, 'Firefox')"

        title = self.sensor._get_active_window_gnome_wayland()
        self.assertEqual(title, "Firefox")

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

        # In my implementation, it might try KWin first if logic dictates, but here it shouldn't if specific GNOME logic is prioritized
        # However, HEAD implementation logic:
        # 1. if KDE in desktop -> kwin
        # 2. if GNOME/UBUNTU in desktop -> gnome
        # 3. fallback -> try both

        # So for "ubuntu:GNOME", it skips 1, hits 2.
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
            if key == "XDG_CURRENT_DESKTOP": return "UnknownDE"
            return default
        mock_env.side_effect = get_env

        # Try KDE first (fails), then GNOME (succeeds)
        mock_kwin.return_value = "Unknown"
        mock_gnome.return_value = "Fallback Window"

        title = self.sensor._get_active_window_linux()
        self.assertEqual(title, "Fallback Window")

        mock_kwin.assert_called_once()
        mock_gnome.assert_called_once()

if __name__ == '__main__':
    unittest.main()
