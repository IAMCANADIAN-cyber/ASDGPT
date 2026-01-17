import unittest
from unittest.mock import MagicMock, patch, ANY
import time
import threading
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.intervention_engine import InterventionEngine

class TestInterventionEngineLogic(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_logic_engine = MagicMock()
        self.mock_logic_engine.get_mode.return_value = "active"

        self.mock_app = MagicMock()
        self.mock_app.data_logger = MagicMock()
        self.mock_app.tray_icon = MagicMock()

        # Patch config values
        self.config_patcher = patch('core.intervention_engine.config')
        self.mock_config = self.config_patcher.start()

        # Default config values for testing
        self.mock_config.MIN_TIME_BETWEEN_INTERVENTIONS = 10
        self.mock_config.FEEDBACK_WINDOW_SECONDS = 30
        self.mock_config.FEEDBACK_SUPPRESSION_MINUTES = 60
        self.mock_config.SUPPRESSIONS_FILE = "user_data/test_suppressions.json"
        self.mock_config.PREFERENCES_FILE = "user_data/test_preferences.json"

        # Instantiate InterventionEngine
        self.intervention_engine = InterventionEngine(self.mock_logic_engine, self.mock_app)

        # Patch internal execution to avoid threads/subprocess
        self.run_thread_patcher = patch.object(self.intervention_engine, '_run_intervention_thread')
        self.mock_run_thread = self.run_thread_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()
        self.run_thread_patcher.stop()
        # Clean up any potential files created (mock should prevent this, but safe practice)

    def test_start_intervention_basic_success(self):
        """Test that start_intervention works under normal conditions."""
        details = {"type": "test", "message": "Test Message", "tier": 1}

        # Ensure rate limit doesn't block
        self.intervention_engine.last_intervention_time = 0

        result = self.intervention_engine.start_intervention(details)

        self.assertTrue(result)
        self.assertTrue(self.intervention_engine._intervention_active.is_set())
        self.mock_run_thread.assert_called_once()
        self.assertEqual(self.intervention_engine._current_intervention_details, details)

    def test_cooldown_blocks_intervention(self):
        """Test that intervention is blocked if called too soon."""
        details = {"type": "test", "message": "Test Message"}

        # Simulate recent intervention
        self.intervention_engine.last_intervention_time = time.time()

        result = self.intervention_engine.start_intervention(details)

        self.assertFalse(result)
        self.mock_run_thread.assert_not_called()

    def test_cooldown_ignored_for_system_notifications(self):
        """Test that system notifications ignore cooldowns."""
        details = {"type": "mode_change_notification", "message": "Mode Changed"}

        # Simulate recent intervention
        self.intervention_engine.last_intervention_time = time.time()

        result = self.intervention_engine.start_intervention(details)

        self.assertTrue(result)
        self.mock_run_thread.assert_called_once()

    def test_preemption_higher_tier(self):
        """Test that a higher tier intervention interrupts an active lower tier one."""
        # Setup active intervention (Tier 1)
        self.intervention_engine._intervention_active.set()
        self.intervention_engine._current_intervention_details = {"type": "low", "tier": 1}

        # Mock stop_intervention to verify it's called
        with patch.object(self.intervention_engine, 'stop_intervention') as mock_stop:
            new_details = {"type": "high", "message": "Urgent", "tier": 2}
            # Ensure cooldown doesn't block
            self.intervention_engine.last_intervention_time = 0

            result = self.intervention_engine.start_intervention(new_details)

            self.assertTrue(result)
            mock_stop.assert_called_once()
            # Verify new one started (mock_run_thread called)
            # Note: start_intervention starts a NEW thread after stopping old.
            # In our mock setup, we just verify the call.
            self.assertTrue(self.intervention_engine._intervention_active.is_set())
            self.assertEqual(self.intervention_engine._current_intervention_details, new_details)

    def test_preemption_rejection_lower_tier(self):
        """Test that a lower tier intervention is rejected if higher tier is active."""
        # Setup active intervention (Tier 2)
        self.intervention_engine._intervention_active.set()
        self.intervention_engine._current_intervention_details = {"type": "high", "tier": 2}

        with patch.object(self.intervention_engine, 'stop_intervention') as mock_stop:
            new_details = {"type": "low", "message": "Not Urgent", "tier": 1}
            self.intervention_engine.last_intervention_time = 0

            result = self.intervention_engine.start_intervention(new_details)

            self.assertFalse(result)
            mock_stop.assert_not_called()
            # LogicEngine logger should log "ignored"
            self.mock_app.data_logger.log_info.assert_called()
            args, _ = self.mock_app.data_logger.log_info.call_args
            self.assertIn("ignored", args[0])

    def test_suppression_logic(self):
        """Test that suppressed interventions are blocked."""
        # Suppress 'annoying_intervention'
        self.intervention_engine.suppressed_interventions = {
            "annoying_intervention": time.time() + 3600 # Valid for 1 hour
        }

        details = {"type": "annoying_intervention", "message": "Hello"}
        self.intervention_engine.last_intervention_time = 0

        result = self.intervention_engine.start_intervention(details)

        self.assertFalse(result)
        self.mock_run_thread.assert_not_called()
        self.mock_app.data_logger.log_info.assert_called()
        args, _ = self.mock_app.data_logger.log_info.call_args
        self.assertIn("suppressed", args[0])

    def test_suppression_expiration(self):
        """Test that expired suppression allows intervention."""
        # Expired suppression
        self.intervention_engine.suppressed_interventions = {
            "annoying_intervention": time.time() - 10
        }

        details = {"type": "annoying_intervention", "message": "Hello"}
        self.intervention_engine.last_intervention_time = 0

        result = self.intervention_engine.start_intervention(details)

        self.assertTrue(result)
        # Verify it was removed from suppression dict
        self.assertNotIn("annoying_intervention", self.intervention_engine.suppressed_interventions)

    def test_mode_blocking(self):
        """Test that interventions are blocked in non-active modes."""
        self.mock_logic_engine.get_mode.return_value = "paused"

        details = {"type": "test", "message": "Test"}
        self.intervention_engine.last_intervention_time = 0

        result = self.intervention_engine.start_intervention(details)

        self.assertFalse(result)
        self.mock_run_thread.assert_not_called()
        self.mock_app.data_logger.log_info.assert_called()
        args, _ = self.mock_app.data_logger.log_info.call_args
        self.assertIn("Intervention suppressed: Mode is paused", args[0])

    def test_get_suppressed_list(self):
        """Verify fetching list of suppressed IDs."""
        future = time.time() + 100
        past = time.time() - 100
        self.intervention_engine.suppressed_interventions = {
            "active_suppression": future,
            "expired_suppression": past
        }

        suppressed_list = self.intervention_engine.get_suppressed_intervention_types()

        self.assertIn("active_suppression", suppressed_list)
        self.assertNotIn("expired_suppression", suppressed_list)
        # Verify expired was cleaned up
        self.assertNotIn("expired_suppression", self.intervention_engine.suppressed_interventions)

    def test_start_intervention_missing_data(self):
        """Test start_intervention with invalid input data."""
        # Missing 'id' AND ('type' + 'message')
        details = {"just_random": "data"}
        self.intervention_engine.last_intervention_time = 0

        result = self.intervention_engine.start_intervention(details)

        self.assertFalse(result)
        self.mock_run_thread.assert_not_called()

    @patch('core.intervention_engine.cv2')
    @patch('core.intervention_engine.os.makedirs')
    @patch('core.intervention_engine.datetime')
    def test_capture_image_execution(self, mock_datetime, mock_makedirs, mock_cv2):
        """Test the _capture_image method logic directly."""
        # Setup prerequisites
        self.intervention_engine.logic_engine.last_video_frame = MagicMock()
        mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"

        # Call method directly
        self.intervention_engine._capture_image("test_capture")

        # Verify makedirs called
        mock_makedirs.assert_called_with("captures")

        # Verify cv2.imwrite called
        mock_cv2.imwrite.assert_called_once()
        args, _ = mock_cv2.imwrite.call_args
        filename = args[0]
        self.assertIn("captures/capture_20240101_120000_test_capture.jpg", filename)
        self.assertEqual(args[1], self.intervention_engine.logic_engine.last_video_frame)

if __name__ == '__main__':
    unittest.main()
