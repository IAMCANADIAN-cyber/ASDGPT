import unittest
from unittest.mock import MagicMock
from core.system_tray import ACRTrayIcon
import config

class TestTooltip(unittest.TestCase):
    def test_tooltip_formatting(self):
        # Mock application
        mock_app = MagicMock()
        tray = ACRTrayIcon(mock_app)

        # Test default (empty dict)
        tray.update_tooltip({})
        expected_initializing = f"{config.APP_NAME}\nInitializing..."
        self.assertEqual(tray.tray_icon.title, expected_initializing)

        # Test with full state (5D)
        state = {
            "arousal": 65,
            "overload": 20,
            "focus": 80,
            "energy": 42,
            "mood": 55
        }
        tray.update_tooltip(state)
        # We expect:
        # ACR
        # A:65 O:20 F:80
        # E:42 M:55
        expected = f"{config.APP_NAME}\nA:65 O:20 F:80\nE:42 M:55"
        self.assertEqual(tray.tray_icon.title, expected)

        # Test with partial state
        partial_state = {"arousal": 30, "energy": 90}
        tray.update_tooltip(partial_state)
        # We expect:
        # ACR
        # A:30
        # E:90
        expected_partial = f"{config.APP_NAME}\nA:30\nE:90"
        self.assertEqual(tray.tray_icon.title, expected_partial)

        print("Tooltip verification passed!")

if __name__ == '__main__':
    unittest.main()
