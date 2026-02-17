import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from sensors.window_sensor import WindowSensor

class TestWindowSensorWayland(unittest.TestCase):

    def setUp(self):
        self.mock_logger = MagicMock()
        # Ensure we start with a clean state for platform checks if needed
        # But most tests mock everything.

    @patch('platform.system')
    @patch('shutil.which')
    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE"}, clear=True)
    @patch('subprocess.run')
    def test_kde_wayland_success(self, mock_subprocess, mock_which, mock_system):
        mock_system.return_value = 'Linux'

        # Setup tools
        def which_side_effect(cmd):
            if cmd == 'qdbus': return '/usr/bin/qdbus'
            return None
        mock_which.side_effect = which_side_effect

        # Setup qdbus output
        mock_res = MagicMock()
        mock_res.returncode = 0
        # Simulated KDE qdbus output
        mock_res.stdout = 'argument 0: a{sv} {\n "caption": [Variant(QString): "Dolphin - Home"],\n "resourceClass": [Variant(QString): "dolphin"]\n}'
        mock_subprocess.return_value = mock_res

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window(sanitize=False)

        self.assertEqual(title, "Dolphin - Home")

        # Verify calls
        args, _ = mock_subprocess.call_args
        cmd = args[0]
        self.assertEqual(cmd, ['qdbus', 'org.kde.KWin', '/KWin', 'org.kde.KWin.activeWindow'])

    @patch('platform.system')
    @patch('shutil.which')
    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME"}, clear=True)
    @patch('subprocess.run')
    def test_gnome_wayland_success(self, mock_subprocess, mock_which, mock_system):
        mock_system.return_value = 'Linux'

        # Setup tools
        def which_side_effect(cmd):
            if cmd == 'gdbus': return '/usr/bin/gdbus'
            return None
        mock_which.side_effect = which_side_effect

        # Setup gdbus output
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "(true, 'Firefox - Web Browser')"
        mock_subprocess.return_value = mock_res

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window(sanitize=False)

        self.assertEqual(title, "Firefox - Web Browser")

        # Verify calls
        args, _ = mock_subprocess.call_args
        cmd = args[0]
        self.assertEqual(cmd[0], 'gdbus')
        self.assertIn('org.gnome.Shell.Eval', cmd)

    @patch('platform.system')
    @patch('shutil.which')
    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME"}, clear=True)
    @patch('subprocess.run')
    def test_gnome_wayland_restricted(self, mock_subprocess, mock_which, mock_system):
        """Test the case where GNOME Shell Eval is restricted (common in modern GNOME)."""
        mock_system.return_value = 'Linux'

        def which_side_effect(cmd):
            if cmd == 'gdbus': return '/usr/bin/gdbus'
            return None
        mock_which.side_effect = which_side_effect

        # Setup gdbus failure
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_res.stderr = "Error: GDBus.Error:org.gnome.Shell.EvalError: Eval is restricted"
        mock_subprocess.return_value = mock_res

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window(sanitize=False)

        self.assertEqual(title, "Unknown")
        # Should log debug message about restriction
        self.mock_logger.log_debug.assert_any_call("GNOME Wayland call failed (Code 1). Eval interface likely restricted.")

    @patch('platform.system')
    @patch('shutil.which')
    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "UnknownDE"}, clear=True)
    @patch('subprocess.run')
    def test_ambiguous_wayland_kde_fallback(self, mock_subprocess, mock_which, mock_system):
        """Test fallback to KDE tool if DE is unknown but qdbus is present."""
        mock_system.return_value = 'Linux'

        # Only qdbus available
        def which_side_effect(cmd):
            if cmd == 'qdbus': return '/usr/bin/qdbus'
            return None
        mock_which.side_effect = which_side_effect

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = '"caption": "Ambiguous Window"'
        mock_subprocess.return_value = mock_res

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window(sanitize=False)

        self.assertEqual(title, "Ambiguous Window")
        # Ensure it called qdbus
        args, _ = mock_subprocess.call_args
        self.assertEqual(args[0][0], 'qdbus')

    @patch('platform.system')
    @patch('shutil.which')
    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE"}, clear=True)
    @patch('subprocess.run')
    def test_kde_wayland_simple_format(self, mock_subprocess, mock_which, mock_system):
        """Test simpler output format for qdbus."""
        mock_system.return_value = 'Linux'

        def which_side_effect(cmd):
            if cmd == 'qdbus': return '/usr/bin/qdbus'
            return None
        mock_which.side_effect = which_side_effect

        mock_res = MagicMock()
        mock_res.returncode = 0
        # Simpler format
        mock_res.stdout = '"caption": "Simple Title"'
        mock_subprocess.return_value = mock_res

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window(sanitize=False)

        self.assertEqual(title, "Simple Title")

    @patch('platform.system')
    @patch('shutil.which')
    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE"}, clear=True)
    @patch('subprocess.run')
    def test_kde_wayland_escaped_quotes(self, mock_subprocess, mock_which, mock_system):
        """Test parsing of titles with escaped quotes."""
        mock_system.return_value = 'Linux'

        def which_side_effect(cmd):
            if cmd == 'qdbus': return '/usr/bin/qdbus'
            return None
        mock_which.side_effect = which_side_effect

        mock_res = MagicMock()
        mock_res.returncode = 0
        # Output with escapes: "My \"Cool\" App"
        mock_res.stdout = '"caption": [Variant(QString): "My \\"Cool\\" App"]'
        mock_subprocess.return_value = mock_res

        sensor = WindowSensor(self.mock_logger)
        title = sensor.get_active_window(sanitize=False)

        self.assertEqual(title, 'My "Cool" App')

    # Dispatch logic tests adapted from upstream
    @patch('sensors.window_sensor.WindowSensor._get_active_window_kwin_wayland')
    @patch('sensors.window_sensor.WindowSensor._get_active_window_gnome_wayland')
    @patch('os.environ.get')
    @patch('platform.system')
    @patch('shutil.which')
    def test_dispatch_gnome_priority(self, mock_which, mock_system, mock_env, mock_gnome, mock_kwin):
        mock_system.return_value = 'Linux'

        def get_env(key, default=None):
            if key == "XDG_SESSION_TYPE": return "wayland"
            if key == "XDG_CURRENT_DESKTOP": return "ubuntu:GNOME"
            return default
        mock_env.side_effect = get_env

        mock_gnome.return_value = "Gnome Window"
        mock_kwin.return_value = "Unknown"

        sensor = WindowSensor(self.mock_logger)
        # Force these available to test dispatch priority
        sensor.gdbus_available = True
        sensor.qdbus_available = True

        title = sensor.get_active_window(sanitize=False)
        self.assertEqual(title, "Gnome Window")

        mock_gnome.assert_called_once()
        mock_kwin.assert_not_called()

if __name__ == '__main__':
    unittest.main()
