import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from sensors.window_sensor import WindowSensor

class TestWindowSensorWayland(unittest.TestCase):

    def setUp(self):
        self.mock_logger = MagicMock()

    @patch('platform.system')
    @patch('shutil.which')
    def test_setup_platform_kde(self, mock_which, mock_system):
        mock_system.return_value = 'Linux'
        # Simulate qdbus availability
        mock_which.side_effect = lambda x: '/usr/bin/qdbus' if x in ['qdbus', 'qdbus-qt5'] else None

        sensor = WindowSensor(self.mock_logger)
        self.assertTrue(getattr(sensor, 'qdbus_available', False))

    @patch('platform.system')
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_gnome_wayland_success(self, mock_subprocess, mock_which, mock_system):
        mock_system.return_value = 'Linux'
        mock_which.return_value = '/usr/bin/gdbus'

        # Set environment to GNOME
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'GNOME', 'XDG_SESSION_TYPE': 'wayland'}):
            sensor = WindowSensor(self.mock_logger)
            sensor.gdbus_available = True # Force availability for test logic

            # Mock gdbus output
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "(true, 'Firefox')"
            mock_subprocess.return_value = mock_res

            title = sensor.get_active_window()
            self.assertEqual(title, "Firefox")

            # Verify gdbus command
            args, _ = mock_subprocess.call_args
            self.assertIn('org.gnome.Shell.Eval', args[0])

    @patch('platform.system')
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_kde_wayland_success(self, mock_subprocess, mock_which, mock_system):
        mock_system.return_value = 'Linux'
        # Simulate qdbus availability
        def which_side_effect(arg):
            if arg in ['qdbus', 'qdbus-qt5']: return '/usr/bin/qdbus'
            return None
        mock_which.side_effect = which_side_effect

        # Set environment to KDE
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'KDE', 'XDG_SESSION_TYPE': 'wayland'}):
            sensor = WindowSensor(self.mock_logger)

            # Mock qdbus output for supportInformation
            # Assuming format: Active Window: Window(0x123 caption="My App")
            mock_res = MagicMock()
            mock_res.returncode = 0
            # A sample chunk of supportInformation
            mock_res.stdout = """
KWin Support Information:
...
Active Window: Window(0x55d4e3a1b0 caption="Konsole — bash")
...
"""
            mock_subprocess.return_value = mock_res

            title = sensor.get_active_window()
            self.assertEqual(title, "Konsole — bash")

            # Verify qdbus command called
            args, _ = mock_subprocess.call_args
            self.assertIn('org.kde.KWin', args[0])
            self.assertIn('supportInformation', args[0])

    @patch('platform.system')
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_kde_wayland_fallback(self, mock_subprocess, mock_which, mock_system):
        mock_system.return_value = 'Linux'
        mock_which.return_value = '/usr/bin/qdbus'

        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'KDE', 'XDG_SESSION_TYPE': 'wayland'}):
            sensor = WindowSensor(self.mock_logger)

            # Mock failure of qdbus
            mock_res = MagicMock()
            mock_res.returncode = 1
            mock_res.stdout = ""
            mock_subprocess.return_value = mock_res

            title = sensor.get_active_window()
            self.assertEqual(title, "Unknown")

if __name__ == '__main__':
    unittest.main()
