import unittest
from unittest.mock import MagicMock, patch
import sys
import importlib

class TestTrayTooltip(unittest.TestCase):
    def setUp(self):
        # Prepare mocks
        self.pystray_mock = MagicMock()
        self.config_mock = MagicMock()
        self.config_mock.APP_NAME = "ASDGPT"
        self.config_mock.SNOOZE_DURATION = 3600

        # Patch sys.modules
        self.modules_patcher = patch.dict(sys.modules, {
            "pystray": self.pystray_mock,
            "PIL": MagicMock(),
            "PIL.Image": MagicMock(),
            "PIL.ImageDraw": MagicMock(),
            "config": self.config_mock
        })
        self.modules_patcher.start()

        # Import and reload the module to ensure it uses the mocked config and dependencies
        import core.system_tray
        importlib.reload(core.system_tray)
        self.ACRTrayIcon = core.system_tray.ACRTrayIcon

        self.mock_app = MagicMock()
        self.tray = self.ACRTrayIcon(self.mock_app)
        # Mock the tray_icon object itself since we mocked pystray
        self.tray.tray_icon = MagicMock()

    def tearDown(self):
        self.modules_patcher.stop()
        # Reload core.system_tray to restore real config if needed by other tests,
        # but patch.dict should handle restoring sys.modules['config'].
        # However, core.system_tray module object itself might hold references to the MOCKED config if it did `from config import ...`.
        # It does `import config`. So it holds reference to the module in sys.modules.
        # Since patch.dict restores the original module in sys.modules,
        # subsequent imports of core.system_tray might see the old (mocked) config if core.system_tray itself isn't reloaded.

        # To be safe, we should unload core.system_tray so it gets re-imported fresh by next test
        if 'core.system_tray' in sys.modules:
            del sys.modules['core.system_tray']

    def test_tooltip_dnd_mode(self):
        self.tray.current_icon_state = "dnd"
        self.tray.update_tooltip({})
        # Expect "ASDGPT (DND)"
        self.assertEqual(self.tray.tray_icon.title, "ASDGPT (DND)")

    def test_tooltip_full_5d_state(self):
        self.tray.current_icon_state = "active"
        state = {
            "arousal": 10,
            "overload": 20,
            "focus": 30,
            "energy": 40,
            "mood": 50
        }
        self.tray.update_tooltip(state)
        # Expected format: "ASDGPT\nA: 10 O: 20 F: 30\nE: 40 M: 50"
        # We verify that all keys are present with their values
        expected_substrings = ["A: 10", "O: 20", "F: 30", "E: 40", "M: 50"]
        actual_title = self.tray.tray_icon.title
        for substring in expected_substrings:
            self.assertIn(substring, actual_title)

    def test_tooltip_partial_state(self):
        self.tray.current_icon_state = "active"
        state = {
            "arousal": 60
        }
        self.tray.update_tooltip(state)
        # Should handle missing keys with "?"
        self.assertIn("A: 60", self.tray.tray_icon.title)
        self.assertIn("E: ?", self.tray.tray_icon.title)
        self.assertIn("F: ?", self.tray.tray_icon.title)
        self.assertIn("O: ?", self.tray.tray_icon.title)
        self.assertIn("M: ?", self.tray.tray_icon.title)

    def test_tooltip_string_state(self):
        self.tray.current_icon_state = "active"
        state = "Initializing..."
        self.tray.update_tooltip(state)
        self.assertIn("Initializing...", self.tray.tray_icon.title)

    def test_snooze_menu_label_default(self):
        """Verify the snooze label generation logic matches the config default"""
        # Reset mock calls
        self.pystray_mock.MenuItem.reset_mock()

        # Ensure default config
        self.config_mock.SNOOZE_DURATION = 3600

        # Re-instantiate
        tray = self.ACRTrayIcon(self.mock_app)

        calls = self.pystray_mock.MenuItem.call_args_list

        found_snooze = False
        for call in calls:
            label = call[0][0]
            if "Snooze" in label:
                self.assertEqual(label, "Snooze for 1 Hour")
                found_snooze = True
                break

        self.assertTrue(found_snooze, "Snooze menu item not found")

    def test_snooze_menu_label_custom(self):
        """Verify the snooze label with custom config"""
        # Patch the SNOOZE_DURATION on the mock config object we injected
        self.config_mock.SNOOZE_DURATION = 1800 # 30 mins

        # We also need to reload the module because the SNOOZE_DURATION is read at __init__ time?
        # No, it's read in __init__. So just changing the attribute on the mock module is enough,
        # PROVIDED that core.system_tray.config points to our mock.

        self.pystray_mock.MenuItem.reset_mock()

        # Re-instantiate
        tray = self.ACRTrayIcon(self.mock_app)

        calls = self.pystray_mock.MenuItem.call_args_list

        found_snooze = False
        for call in calls:
            label = call[0][0]
            if "Snooze" in label:
                self.assertEqual(label, "Snooze for 30 Minutes")
                found_snooze = True
                break
        self.assertTrue(found_snooze, "Snooze menu item not found for 30 mins")

    def test_snooze_menu_label_custom_hours(self):
        """Verify the snooze label with custom config (2 hours)"""
        self.config_mock.SNOOZE_DURATION = 7200 # 2 hours

        self.pystray_mock.MenuItem.reset_mock()

        tray = self.ACRTrayIcon(self.mock_app)
        calls = self.pystray_mock.MenuItem.call_args_list

        found_snooze = False
        for call in calls:
            label = call[0][0]
            if "Snooze" in label:
                self.assertEqual(label, "Snooze for 2 Hours")
                found_snooze = True
                break
        self.assertTrue(found_snooze, "Snooze menu item not found for 2 hours")

if __name__ == "__main__":
    unittest.main()
