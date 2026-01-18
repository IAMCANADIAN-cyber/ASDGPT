import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import threading
import time

# Mock dependencies before import
sys.modules["pystray"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["PIL.ImageDraw"] = MagicMock()
sys.modules["config"] = MagicMock()
sys.modules["config"].APP_NAME = "ASDGPT"
sys.modules["config"].SNOOZE_DURATION = 3600

from core.system_tray import ACRTrayIcon

class TestSystemTrayCoverage(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.logic_engine = MagicMock()
        self.mock_app.logic_engine.get_mode.return_value = "active"
        self.mock_app.intervention_engine = MagicMock()

        self.tray = ACRTrayIcon(self.mock_app)
        self.tray.tray_icon = MagicMock()

    def test_init_load_image_fallback(self):
        """Test image loading fallback mechanism."""
        # Unmock PIL temporarily for this test or mock side_effect to raise Error
        with patch('core.system_tray.Image.open', side_effect=Exception("File not found")):
            # It should catch exception and return a fallback image
            with patch('core.system_tray.Image.new') as mock_new:
                from core.system_tray import load_image
                img = load_image("non_existent.png")
                mock_new.assert_called()
                self.assertIsNotNone(img)

    def test_run_threaded(self):
        """Test that run_threaded starts a thread."""
        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            self.tray.run_threaded()

            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
            self.assertIsNotNone(self.tray.thread)

    def test_stop(self):
        """Test stopping the tray icon."""
        self.tray.thread = MagicMock()
        self.tray.thread.is_alive.return_value = True

        self.tray.stop()

        self.tray.tray_icon.stop.assert_called_once()
        self.tray.thread.join.assert_called_once()

    def test_on_toggle_pause_resume(self):
        """Test pause/resume callback."""
        self.tray.on_toggle_pause_resume(None, None)
        self.mock_app.on_pause_resume_pressed.assert_called_once()

    def test_on_snooze_active_to_snoozed(self):
        """Test snooze callback when currently active."""
        self.mock_app.logic_engine.get_mode.side_effect = ["active", "snoozed"] # Before, After

        self.tray.on_snooze(None, None)

        self.mock_app.logic_engine.set_mode.assert_called_with("snoozed")
        self.mock_app.intervention_engine.notify_mode_change.assert_called_with("snoozed")
        # Verify icon update logic (can't easily check internal state update without more mocking, but method call is safe)

    def test_on_snooze_already_snoozed(self):
        """Test snooze callback when already snoozed."""
        self.mock_app.logic_engine.get_mode.return_value = "snoozed"

        self.tray.on_snooze(None, None)

        self.mock_app.logic_engine.set_mode.assert_not_called()

    def test_on_toggle_dnd_active_to_dnd(self):
        """Test DND toggle from active to DND."""
        self.mock_app.logic_engine.get_mode.side_effect = ["active", "dnd"]

        self.tray.on_toggle_dnd(None, None)

        self.mock_app.logic_engine.set_mode.assert_called_with("dnd")

    def test_on_toggle_dnd_dnd_to_active(self):
        """Test DND toggle from DND to active."""
        self.mock_app.logic_engine.get_mode.side_effect = ["dnd", "active"]

        self.tray.on_toggle_dnd(None, None)

        self.mock_app.logic_engine.set_mode.assert_called_with("active")

    def test_on_feedback_callbacks(self):
        """Test feedback callbacks."""
        self.tray.on_feedback_helpful(None, None)
        self.mock_app.on_feedback_helpful_pressed.assert_called_once()

        self.tray.on_feedback_unhelpful(None, None)
        self.mock_app.on_feedback_unhelpful_pressed.assert_called_once()

    def test_on_quit(self):
        """Test quit callback."""
        self.tray.on_quit(None, None)
        self.mock_app.quit_application.assert_called_once()
        self.tray.tray_icon.stop.assert_called()

    def test_update_icon_status_valid(self):
        """Test updating icon with valid status."""
        self.tray.update_icon_status("paused")
        self.assertEqual(self.tray.current_icon_state, "paused")

    def test_update_icon_status_invalid(self):
        """Test updating icon with invalid status."""
        self.tray.update_icon_status("invalid_status")
        self.assertEqual(self.tray.current_icon_state, "default")

    def test_flash_icon(self):
        """Test flash_icon starts a thread."""
        with patch('threading.Thread') as mock_thread:
            self.tray.flash_icon("error")
            mock_thread.assert_called()

    def test_notify_user(self):
        """Test notify_user calls pystray notify."""
        self.tray.notify_user("Title", "Message")
        self.tray.tray_icon.notify.assert_called_with("Message", "Title")

if __name__ == '__main__':
    unittest.main()
