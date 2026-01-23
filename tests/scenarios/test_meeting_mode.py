import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.logic_engine import LogicEngine
import config

class TestMeetingMode(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_lmm = MagicMock()

        # Initialize LogicEngine
        self.logic = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm
        )
        # Enable tracking manually as we don't have main.py hook
        self.logic.input_tracking_enabled = True

    @patch('core.logic_engine.time.time')
    def test_meeting_entry(self, mock_time):
        """Test transitioning to DND when meeting conditions are met."""
        # Start time
        start_time = 1000.0
        mock_time.return_value = start_time

        # Reset LogicEngine timestamps
        self.logic.last_user_input_time = start_time - 20.0 # Idle for 20s (>10s threshold)
        self.logic.continuous_speech_start_time = 0

        # --- Step 1: Start Speech ---
        # Mock sensors to report speech + face
        self.logic.audio_analysis = {"is_speech": True}
        self.logic.face_metrics = {"face_detected": True}

        self.logic.update()

        # Speech start time should be set to current time
        self.assertEqual(self.logic.continuous_speech_start_time, start_time)
        self.assertEqual(self.logic.current_mode, "active")

        # --- Step 2: Continue Speech for 3.1s ---
        current_time = start_time + 3.1
        mock_time.return_value = current_time

        self.logic.update()

        # Should now be in DND
        self.assertEqual(self.logic.current_mode, "dnd")
        self.assertTrue(self.logic.auto_dnd_active)

    @patch('core.logic_engine.time.time')
    def test_meeting_grace_period_failure(self, mock_time):
        """
        Test that gaps in speech reset the timer (Current Behavior)
        OR don't reset (Desired Behavior).
        This test expects the Desired Behavior, so it should FAIL initially.
        """
        start_time = 2000.0
        mock_time.return_value = start_time

        self.logic.last_user_input_time = start_time - 20.0
        self.logic.continuous_speech_start_time = 0

        # --- Step 1: Speech for 1.0s ---
        self.logic.audio_analysis = {"is_speech": True}
        self.logic.face_metrics = {"face_detected": True}
        self.logic.update() # Start timer

        mock_time.return_value = start_time + 1.0
        self.logic.update() # Speech continues
        self.assertEqual(self.logic.continuous_speech_start_time, start_time)

        # --- Step 2: Silence for 0.5s ---
        # Gap!
        mock_time.return_value = start_time + 1.5
        self.logic.audio_analysis = {"is_speech": False} # Silence
        self.logic.update()

        # Current Behavior: Reset to 0 (Test should fail here if asserting > 0)
        # Desired: Maintain start_time
        # We assert desired behavior to demonstrate failure
        self.assertEqual(self.logic.continuous_speech_start_time, start_time,
                         "Speech timer reset during short gap (Grace period missing)")

        # --- Step 3: Speech resumes ---
        mock_time.return_value = start_time + 3.1
        self.logic.audio_analysis = {"is_speech": True}
        self.logic.update()

        # Should reach threshold (3.1s total elapsed, gap was small)
        self.assertEqual(self.logic.current_mode, "dnd")

    @patch('core.logic_engine.time.time')
    def test_meeting_exit(self, mock_time):
        """Test exiting DND when user input detected."""
        start_time = 3000.0
        mock_time.return_value = start_time

        # Set to DND (Auto)
        self.logic.current_mode = "dnd"
        self.logic.auto_dnd_active = True
        self.logic.last_user_input_time = start_time - 5.0 # Idle

        # Verify stay in DND if idle
        self.logic.update()
        self.assertEqual(self.logic.current_mode, "dnd")

        # User Types!
        self.logic.last_user_input_time = start_time # input NOW
        self.logic.update()

        # Should revert to active
        self.assertEqual(self.logic.current_mode, "active")
        self.assertFalse(self.logic.auto_dnd_active)

if __name__ == '__main__':
    unittest.main()
