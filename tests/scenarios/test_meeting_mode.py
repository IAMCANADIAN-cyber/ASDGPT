import unittest
from unittest.mock import MagicMock, patch
import time
from core.logic_engine import LogicEngine
import config

class TestMeetingMode(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()

        # Patch config values for predictable testing
        self.config_patcher = patch.multiple(
            'core.logic_engine.config',
            MEETING_MODE_SPEECH_DURATION_THRESHOLD=3.0,
            MEETING_MODE_IDLE_KEYBOARD_THRESHOLD=5.0,
            MEETING_MODE_SPEECH_GRACE_PERIOD=2.0
        )
        self.config_patcher.start()

        self.engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger
        )
        self.engine.input_tracking_enabled = True # Simulate keyboard hook active

    def tearDown(self):
        self.config_patcher.stop()

    @patch('core.logic_engine.time.time')
    def test_meeting_mode_trigger(self, mock_time):
        """Test basic triggering of Meeting Mode (Auto-DND)."""
        start_time = 1000.0
        mock_time.return_value = start_time

        # Initial state
        self.engine.last_user_input_time = start_time - 10.0 # Idle enough (10s > 5s)

        # 1. Start Speech
        # Update 1: Speech starts
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}
        self.engine.update()

        self.assertEqual(self.engine.continuous_speech_start_time, start_time)
        self.assertEqual(self.engine.current_mode, "active")

        # 2. Continue Speech (2 seconds later)
        mock_time.return_value = start_time + 2.0
        self.engine.update()
        self.assertEqual(self.engine.current_mode, "active") # Not yet 3s

        # 3. Hit Threshold (3.5 seconds later)
        mock_time.return_value = start_time + 3.5
        self.engine.update()

        # Should switch to DND
        self.assertEqual(self.engine.current_mode, "dnd")
        self.assertTrue(self.engine.auto_dnd_active)

    @patch('core.logic_engine.time.time')
    def test_speech_grace_period(self, mock_time):
        """Test that short gaps in speech do not reset the timer."""
        start_time = 1000.0
        mock_time.return_value = start_time

        self.engine.last_user_input_time = start_time - 10.0

        # 1. Speech Starts
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}
        self.engine.update()

        # 2. Speech Stops (1s later) - Grace period should start
        mock_time.return_value = start_time + 1.0
        self.engine.audio_analysis = {"is_speech": False} # Silence
        self.engine.update()

        self.assertEqual(self.engine.continuous_speech_start_time, start_time)
        self.assertGreater(self.engine.meeting_mode_grace_period_end_time, 0)

        # 3. Speech Resumes (1.5s later, so 0.5s gap < 2.0s grace)
        mock_time.return_value = start_time + 1.5
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.update()

        self.assertEqual(self.engine.continuous_speech_start_time, start_time) # Should NOT have reset
        self.assertEqual(self.engine.meeting_mode_grace_period_end_time, 0) # Should reset grace period

        # 4. Trigger Threshold (3.5s total time)
        mock_time.return_value = start_time + 3.5
        self.engine.update()
        self.assertEqual(self.engine.current_mode, "dnd")

    @patch('core.logic_engine.time.time')
    def test_speech_timeout(self, mock_time):
        """Test that long gaps reset the timer."""
        start_time = 1000.0
        mock_time.return_value = start_time

        self.engine.last_user_input_time = start_time - 10.0

        # 1. Speech Starts
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}
        self.engine.update()

        # 2. Speech Stops
        mock_time.return_value = start_time + 1.0
        self.engine.audio_analysis = {"is_speech": False}
        self.engine.update()

        # 3. Long Gap (3.5s later -> 2.5s gap > 2.0s grace)
        mock_time.return_value = start_time + 3.5
        self.engine.update()

        self.assertEqual(self.engine.continuous_speech_start_time, 0)
        self.assertEqual(self.engine.meeting_mode_grace_period_end_time, 0)
        self.assertEqual(self.engine.current_mode, "active")

    @patch('core.logic_engine.time.time')
    def test_meeting_mode_exit(self, mock_time):
        """Test exiting DND mode via user input."""
        start_time = 1000.0
        mock_time.return_value = start_time

        # Force into Auto-DND
        self.engine.current_mode = "dnd"
        self.engine.auto_dnd_active = True
        self.engine.last_user_input_time = start_time - 10.0 # Idle

        # 1. Update (Idle) -> Stay in DND
        self.engine.update()
        self.assertEqual(self.engine.current_mode, "dnd")

        # 2. User Input (Simulate keypress updating timestamp)
        # In real app, keyboard hook calls register_user_input()
        self.engine.last_user_input_time = start_time + 1.0
        mock_time.return_value = start_time + 1.5 # 0.5s idle

        self.engine.update()

        self.assertEqual(self.engine.current_mode, "active")
        self.assertFalse(self.engine.auto_dnd_active)

if __name__ == '__main__':
    unittest.main()
