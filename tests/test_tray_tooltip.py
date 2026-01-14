import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock pystray and PIL before importing ACRTrayIcon
sys.modules["pystray"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["PIL.ImageDraw"] = MagicMock()

# Mock config
sys.modules["config"] = MagicMock()
sys.modules["config"].APP_NAME = "ASDGPT"

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
        # Expected format: "ASDGPT\nA: 10 | O: 20 | F: 30 | E: 40 | M: 50"
        # Note: The order might vary depending on implementation, but let's aim for A | O | F | E | M or similar.
        # The current implementation only has A | E | F. I'm writing the test for the DESIRED state.
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

if __name__ == "__main__":
    unittest.main()
