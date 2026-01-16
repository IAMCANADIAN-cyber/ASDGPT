import unittest
from unittest.mock import MagicMock, patch, ANY
import time
import numpy as np
import sys
import os
import threading

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.logic_engine import LogicEngine
import config

class TestLogicEngineMethods(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_logger = MagicMock()
        self.mock_lmm = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()

        # Instantiate LogicEngine with mocks
        self.engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm
        )

        # Reset defaults for easier testing
        self.engine.doom_scroll_trigger_threshold = 3

    def test_process_visual_context_triggers_doom_scroll(self):
        """Test detection of doom scrolling via persistent visual tags."""
        # Case 1: Single occurrence - no trigger
        result = self.engine._process_visual_context_triggers(["phone_usage"])
        self.assertIsNone(result)
        self.assertEqual(self.engine.context_persistence["phone_usage"], 1)

        # Case 2: Second occurrence
        result = self.engine._process_visual_context_triggers(["phone_usage", "other_tag"])
        self.assertIsNone(result)
        self.assertEqual(self.engine.context_persistence["phone_usage"], 2)

        # Case 3: Threshold reached (3rd)
        result = self.engine._process_visual_context_triggers(["phone_usage"])
        self.assertEqual(result, "doom_scroll_breaker")
        self.assertEqual(self.engine.context_persistence["phone_usage"], 3)

        # Case 4: Interruption resets count
        result = self.engine._process_visual_context_triggers(["messy_room"]) # phone_usage missing
        self.assertIsNone(result)
        self.assertEqual(self.engine.context_persistence["phone_usage"], 0)
        self.assertEqual(self.engine.context_persistence["messy_room"], 1)

    def test_set_mode_unlocked_transitions(self):
        """Test mode transitions and side effects."""
        # Initial state is active (default in config usually)

        # Transition to Snoozed
        self.engine.set_mode("snoozed")
        self.assertEqual(self.engine.current_mode, "snoozed")
        self.assertTrue(self.engine.snooze_end_time > time.time())

        # Transition back to Active (manual)
        self.engine.set_mode("active")
        self.assertEqual(self.engine.current_mode, "active")
        self.assertEqual(self.engine.snooze_end_time, 0)

        # Transition to Paused
        self.engine.set_mode("paused")
        self.assertEqual(self.engine.current_mode, "paused")
        self.assertEqual(self.engine.previous_mode_before_pause, "active")

        # Toggle Pause/Resume (back to active)
        self.engine.toggle_pause_resume()
        self.assertEqual(self.engine.current_mode, "active")

        # Invalid mode
        self.engine.set_mode("invalid_mode")
        self.assertEqual(self.engine.current_mode, "active") # Should stay same

    def test_set_mode_error_probation(self):
        """Test transition from error to active triggers probation."""
        self.engine.current_mode = "error"

        current_time = time.time()
        self.engine.set_mode("active")
        self.assertEqual(self.engine.current_mode, "active")
        # Verify probation end time is set
        self.assertTrue(self.engine.recovery_probation_end_time >= current_time + self.engine.recovery_probation_duration)

    def test_sensor_fallback_processing(self):
        """Test processing methods when sensors lack advanced methods."""
        # Setup engine with "dumb" sensors (mocks without expected methods)
        dumb_audio = MagicMock()
        del dumb_audio.analyze_chunk # Ensure it doesn't have the method
        dumb_video = MagicMock()
        del dumb_video.process_frame

        engine = LogicEngine(
            audio_sensor=dumb_audio,
            video_sensor=dumb_video,
            logger=self.mock_logger
        )

        # Audio Fallback
        chunk = np.array([0.1, 0.1, 0.1])
        engine.process_audio_data(chunk)
        self.assertAlmostEqual(engine.audio_level, 0.1, places=5)
        self.assertEqual(engine.audio_analysis["rms"], engine.audio_level)

        # Video Fallback (frame diff)
        frame1 = np.zeros((10, 10, 3), dtype=np.uint8)
        frame2 = np.ones((10, 10, 3), dtype=np.uint8) * 10

        engine.process_video_data(frame1)
        self.assertEqual(engine.video_activity, 0.0) # First frame, no diff

        engine.process_video_data(frame2)
        # Activity should be mean of diff (10)
        self.assertAlmostEqual(engine.video_activity, 10.0, delta=1.0)

    def test_shutdown(self):
        """Test shutdown mechanism."""
        # Start a dummy thread to simulate LMM
        def dummy_task():
            time.sleep(0.1)

        self.engine.lmm_thread = threading.Thread(target=dummy_task)
        self.engine.lmm_thread.start()

        self.engine.shutdown()

        # Verify it waited and thread is likely dead or joined
        self.assertFalse(self.engine.lmm_thread.is_alive())

    def test_lmm_circuit_breaker(self):
        """Test that circuit breaker prevents calls."""
        self.engine.lmm_circuit_breaker_open_until = time.time() + 100

        self.engine._trigger_lmm_analysis(reason="test")

        # Should not have started a thread
        self.assertIsNone(self.engine.lmm_thread)
        self.mock_logger.log_debug.assert_called()

if __name__ == '__main__':
    unittest.main()
