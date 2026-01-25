import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import importlib

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestTrayFeedback(unittest.TestCase):
    def setUp(self):
        # Create patches for sys.modules
        self.modules_patcher = patch.dict(sys.modules, {
            "pystray": MagicMock(),
            "PIL": MagicMock(),
            "PIL.Image": MagicMock(),
            "PIL.ImageDraw": MagicMock(),
            "config": MagicMock()
        })
        self.modules_patcher.start()

        # Setup mock config attributes
        sys.modules["config"].APP_NAME = "ASDGPT"
        sys.modules["config"].SNOOZE_DURATION = 3600

        # Reload module to pick up mocked dependencies
        import core.system_tray
        importlib.reload(core.system_tray)
        self.ACRTrayIcon = core.system_tray.ACRTrayIcon

        self.mock_app = MagicMock()
        self.tray = self.ACRTrayIcon(self.mock_app)
        self.tray.tray_icon = MagicMock()

    def tearDown(self):
        self.modules_patcher.stop()
        # Clean up core.system_tray from sys.modules so it gets reloaded with real dependencies next time
        if 'core.system_tray' in sys.modules:
            del sys.modules['core.system_tray']

    def test_feedback_icons_initialized(self):
        """Verify that feedback icons are created during initialization."""
        self.assertIn("feedback_helpful", self.tray.icons)
        self.assertIn("feedback_unhelpful", self.tray.icons)
        # Verify that create_colored_icon was likely used (we can't easily check internal calls of __init__,
        # but we can check existence).

    @patch('core.system_tray.Image.new')
    @patch('core.system_tray.ImageDraw.Draw')
    def test_create_colored_icon(self, mock_draw, mock_image_new):
        """Test the create_colored_icon helper."""
        self.tray.create_colored_icon("blue", "TEST")

        mock_image_new.assert_called_with('RGB', (64, 64), color="blue")
        # Check that text was drawn
        mock_draw_instance = mock_draw.return_value
        mock_draw_instance.text.assert_called()
        args, _ = mock_draw_instance.text.call_args
        self.assertEqual(args[1], "TEST")

    @patch('threading.Thread')
    def test_flash_icon_logic(self, mock_thread):
        """Test that flash_icon starts a thread with correct target."""
        self.tray.flash_icon("feedback_helpful", duration=0.1)

        mock_thread.assert_called_once()
        # Get the target function passed to Thread
        args, kwargs = mock_thread.call_args
        target = kwargs.get('target')

        # We can execute the target to verify it calls update_icon_status
        # We need to mock time.sleep to avoid waiting
        with patch('time.sleep') as mock_sleep:
            # Also mock update_icon_status to track calls
            self.tray.update_icon_status = MagicMock()

            target() # Run the flash logic

            # Should switch to flash_status, then back to original, repeated 'flashes' times (default 2)
            # Sequence: Flash -> Orig -> Flash -> Orig -> Ensure Orig
            # Total calls = 2 * 2 + 1 = 5 calls to update_icon_status?
            # Code:
            # for _ in range(flashes):
            #     update(flash)
            #     sleep
            #     update(orig)
            #     sleep
            # update(orig)

            # Default flashes=2.
            # Iter 1: update(flash), update(orig)
            # Iter 2: update(flash), update(orig)
            # End: update(orig)
            # Total 5 calls.

            self.assertEqual(self.tray.update_icon_status.call_count, 5)

            calls = self.tray.update_icon_status.call_args_list
            self.assertEqual(calls[0], call("feedback_helpful"))
            self.assertEqual(calls[1], call("default")) # original was default
            self.assertEqual(calls[2], call("feedback_helpful"))
            self.assertEqual(calls[3], call("default"))
            self.assertEqual(calls[4], call("default"))

if __name__ == "__main__":
    unittest.main()
