import unittest
from unittest.mock import MagicMock, patch
import time
import threading
import config
from core.logic_engine import LogicEngine

class TestLogicEngineLifecycle(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.engine = LogicEngine(logger=self.mock_logger)

        # Reset defaults
        self.engine.lmm_call_interval = 60
        self.engine.min_lmm_interval = 10

    def test_snooze_expiry(self):
        """Test that update() transitions from SNOOZED to ACTIVE when time expires."""
        self.engine.set_mode("snoozed")
        self.engine.snooze_end_time = time.time() - 1 # Expired

        # Mock callback
        mock_callback = MagicMock()
        self.engine.tray_callback = mock_callback

        self.engine.update()

        self.assertEqual(self.engine.current_mode, "active")
        self.assertEqual(self.engine.snooze_end_time, 0)

        # Check notification
        mock_callback.assert_called_with(new_mode="active", old_mode="snoozed")

    def test_error_mode_recovery_loop(self):
        """Test the error recovery loop in update()."""
        self.engine.current_mode = "error"
        self.engine.previous_mode_before_pause = "active"
        self.engine.error_recovery_interval = 0.1 # Fast recovery check
        self.engine.last_error_recovery_attempt_time = time.time() - 1
        self.engine.max_error_recovery_attempts = 2

        # 1. First attempt
        self.engine.update()
        self.assertEqual(self.engine.error_recovery_attempts, 1)
        self.assertEqual(self.engine.current_mode, "active")

        # LogicEngine sets it to 'active' on recovery attempt.
        # To test failure, we must force it back to error externally (simulating sensor failure)
        self.engine.current_mode = "error"
        self.engine.last_error_recovery_attempt_time = time.time() - 1

        # 2. Second attempt
        self.engine.update()
        self.assertEqual(self.engine.error_recovery_attempts, 2)
        self.engine.current_mode = "error"
        self.engine.last_error_recovery_attempt_time = time.time() - 1

        # 3. Max attempts reached -> Notification
        mock_notif = MagicMock()
        self.engine.notification_callback = mock_notif

        self.engine.update()
        self.assertEqual(self.engine.error_recovery_attempts, 3) # Incremented to stop notifying
        mock_notif.assert_called_with("System Error", unittest.mock.ANY)

    def test_state_update_callback(self):
        """Test that state_update_callback is called after LMM analysis."""
        # Disable smoothing for this test
        from collections import deque
        self.engine.state_engine.history_size = 1
        self.engine.state_engine.history = {
            k: deque([v[0]], maxlen=1) for k, v in self.engine.state_engine.history.items()
        }

        mock_lmm = MagicMock()
        mock_lmm.process_data.return_value = {
            "state_estimation": {"arousal": 10, "overload": 10, "focus": 10, "energy": 10, "mood": 10}
        }
        self.engine.lmm_interface = mock_lmm

        mock_state_callback = MagicMock()
        self.engine.state_update_callback = mock_state_callback

        # Trigger LMM analysis directly via internal method for sync testing of the logic
        # (normally async, but we can verify the method called by thread)
        payload = {
            "video_data": None, "audio_data": None,
            "user_context": {"sensor_metrics": {}}
        }
        self.engine._run_lmm_analysis_async(payload, allow_intervention=False)

        mock_state_callback.assert_called()
        args, _ = mock_state_callback.call_args
        self.assertEqual(args[0]["arousal"], 10)

    def test_shutdown_timeout(self):
        """Test that shutdown doesn't hang indefinitely if LMM thread is stuck."""
        def blocking_task():
            time.sleep(5) # Longer than shutdown timeout (approx 2s in code)

        self.engine.lmm_thread = threading.Thread(target=blocking_task, daemon=True)
        self.engine.lmm_thread.start()

        start_time = time.time()
        self.engine.shutdown()
        duration = time.time() - start_time

        # Should finish around 2s (timeout), definitely less than 5s
        self.assertTrue(duration < 4.0)
        self.mock_logger.log_warning.assert_called_with("LMM analysis thread did not finish in time (will be killed as daemon).")

if __name__ == '__main__':
    unittest.main()
