import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.logic_engine import LogicEngine

class TestLogicEngineRecovery(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_lmm = MagicMock()

        self.engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm
        )

        # Defaults from code/config
        self.engine.error_recovery_interval = 5
        self.engine.max_error_recovery_attempts = 3
        self.engine.recovery_probation_duration = 10

    def test_error_mode_logging_throttled(self):
        """Test that debug logs in error mode are throttled."""
        self.engine.current_mode = "error"
        self.engine.last_error_log_time = 0
        # Ensure we don't trigger recovery immediately
        self.engine.last_error_recovery_attempt_time = 100.0

        # 1. First update - should log
        with patch('time.time', return_value=100.0):
            self.engine.update()
            self.mock_logger.log_debug.assert_called_with("LogicEngine: Mode is ERROR. Attempting to handle or log.")
            self.assertEqual(self.engine.last_error_log_time, 100.0)

        self.mock_logger.reset_mock()

        # 2. Immediate update (t=101) - should NOT log (interval 10s)
        with patch('time.time', return_value=101.0):
            self.engine.update()
            self.mock_logger.log_debug.assert_not_called()

        # 3. Later update (t=111) - should log
        with patch('time.time', return_value=111.0):
            self.engine.update()
            self.mock_logger.log_debug.assert_called()

    def test_error_recovery_attempt(self):
        """Test that system attempts to recover to active mode after interval."""
        self.engine.current_mode = "error"
        self.engine.previous_mode_before_pause = "active"
        self.engine.last_error_recovery_attempt_time = 100.0
        self.engine.error_recovery_attempts = 0

        # 1. Update before interval (t=101, interval=5) - No attempt
        with patch('time.time', return_value=101.0):
            self.engine.update()
            self.assertEqual(self.engine.current_mode, "error")
            self.assertEqual(self.engine.error_recovery_attempts, 0)

        # 2. Update after interval (t=106) - Attempt recovery
        with patch('time.time', return_value=106.0):
            self.engine.update()
            # Should have transitioned to active (via set_mode logic inside update)
            # update calls set_mode("active")
            self.assertEqual(self.engine.current_mode, "active")
            self.assertEqual(self.engine.error_recovery_attempts, 1)
            self.assertEqual(self.engine.last_error_recovery_attempt_time, 106.0)

    def test_error_recovery_max_attempts(self):
        """Test that system stops trying after max attempts and notifies user."""
        self.engine.current_mode = "error"
        self.engine.error_recovery_attempts = self.engine.max_error_recovery_attempts
        self.engine.notification_callback = MagicMock()

        # Force time to be well past any interval
        with patch('time.time', return_value=1000.0):
            self.engine.update()

        # Should log error about max attempts
        self.mock_logger.log_error.assert_called_with("Max error recovery attempts reached. User intervention required.")

        # Should call notification callback
        self.engine.notification_callback.assert_called_with("System Error", "The system has encountered a persistent error and could not recover automatically. Please check logs.")

        # Should increment attempts one last time to prevent spam
        self.assertEqual(self.engine.error_recovery_attempts, self.engine.max_error_recovery_attempts + 1)

    def test_error_recovery_probation_success(self):
        """Test that staying in active mode long enough clears the error count."""
        # Simulate successful recovery
        self.engine.current_mode = "active"
        self.engine.error_recovery_attempts = 2
        self.engine.recovery_probation_end_time = 100.0

        # 1. Update during probation (t=90) - No change
        with patch('time.time', return_value=90.0):
            self.engine.update()
            self.assertEqual(self.engine.error_recovery_attempts, 2)

        # 2. Update after probation (t=101) - Reset attempts
        with patch('time.time', return_value=101.0):
            self.engine.update()
            self.assertEqual(self.engine.error_recovery_attempts, 0)
            self.assertEqual(self.engine.recovery_probation_end_time, 0)

if __name__ == '__main__':
    unittest.main()
