import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock pystray and PIL before importing ACRTrayIcon
sys.modules["pystray"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["PIL.ImageDraw"] = MagicMock()

# Import real config instead of mocking the whole module to avoid breaking other tests
import config
if not hasattr(config, "APP_NAME"):
    config.APP_NAME = "ASDGPT"
if not hasattr(config, "SNOOZE_DURATION"):
    config.SNOOZE_DURATION = 3600

from core.system_tray import ACRTrayIcon

class TestTrayTooltip(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.tray = ACRTrayIcon(self.mock_app)
        # Mock the tray_icon object itself since we mocked pystray
        self.tray.tray_icon = MagicMock()

    def test_tooltip_dnd_mode(self):
        self.tray.current_icon_state = "dnd"
        self.tray.update_tooltip({})
        # Expect "ACR (DND)" because defaults in config.py say APP_NAME = "ACR"
        # and we are now using the real config.
        # However, for consistency with the test environment, we should verify against config.APP_NAME
        expected_title = f"{config.APP_NAME} (DND)"
        self.assertEqual(self.tray.tray_icon.title, expected_title)

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
        # Reset mock to ensure we don't catch previous calls
        sys.modules["pystray"].MenuItem.reset_mock()
        # Reset config to default in case it was patched elsewhere
        sys.modules["config"].SNOOZE_DURATION = 3600

        # Re-instantiate to catch the __init__ logic with default config (3600s)
        tray = ACRTrayIcon(self.mock_app)

        # Access the private menu object to verify the label
        # pystray.Icon(..., menu=...)
        # tray.tray_icon.menu is a Tuple of MenuItems
        # We need to find the item with 'Snooze' in the text

        # Since we mocked pystray, we need to inspect how the mock was called
        # The constructor calls pystray.MenuItem multiple times

        # Instead of inspecting the mock calls which can be messy,
        # let's trust that the logic inside __init__ is what we want to test.
        # But we can't easily test __init__ logic without inspecting the mock calls.

        # Let's inspect the mock calls to pystray.MenuItem
        calls = sys.modules["pystray"].MenuItem.call_args_list

        # Find the call where the first arg contains 'Snooze'
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
        with patch('config.SNOOZE_DURATION', 1800): # 30 mins
             # Re-instantiate
            tray = ACRTrayIcon(self.mock_app)

            # Inspect calls again (they append to the list)
            # We need to look at the MOST RECENT calls or just filter all
            # Since we can't easily reset the mock history for the module-level mock here without affecting others?
            # Actually we can reset the mock
            # sys.modules["pystray"].MenuItem.reset_mock()
            # But let's just search in the new calls.

            # Let's reset the mock for this test
            sys.modules["pystray"].MenuItem.reset_mock()

            tray = ACRTrayIcon(self.mock_app)
            calls = sys.modules["pystray"].MenuItem.call_args_list

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
        with patch('config.SNOOZE_DURATION', 7200): # 2 hours
            sys.modules["pystray"].MenuItem.reset_mock()

            tray = ACRTrayIcon(self.mock_app)
            calls = sys.modules["pystray"].MenuItem.call_args_list

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
