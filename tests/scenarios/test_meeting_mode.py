import time
import unittest
from unittest.mock import MagicMock, patch
from core.logic_engine import LogicEngine
import config

class TestMeetingMode(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_lmm = MagicMock()

        # Instantiate LogicEngine with mocks
        self.engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm
        )

        # Override config thresholds for faster testing
        self.original_speech_threshold = getattr(config, 'MEETING_MODE_SPEECH_DURATION_THRESHOLD', 3.0)
        self.original_idle_threshold = getattr(config, 'MEETING_MODE_IDLE_KEYBOARD_THRESHOLD', 10.0)
        self.original_grace_period = getattr(config, 'MEETING_MODE_SPEECH_GRACE_PERIOD', 2.0)

        # Set short thresholds
        config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = 0.5
        config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = 1.0
        config.MEETING_MODE_SPEECH_GRACE_PERIOD = 0.3 # Short grace period for testing

    def tearDown(self):
        # Restore config
        config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = self.original_speech_threshold
        config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = self.original_idle_threshold
        config.MEETING_MODE_SPEECH_GRACE_PERIOD = self.original_grace_period

    def test_meeting_mode_triggers(self):
        """Test that meeting mode triggers when all conditions are met."""
        self.engine.current_mode = "active"

        # 1. Simulate "User Input Tracking Enabled" (hook worked)
        self.engine.input_tracking_enabled = True
        # Simulate idle time (last input was 2 seconds ago) -> Idle Threshold (1.0s) met
        self.engine.last_user_input_time = time.time() - 2.0

        # 2. Simulate Sensor Data
        # Audio: Speech detected
        self.engine.audio_analysis = {"is_speech": True, "rms": 0.5}
        # Video: Face detected
        self.engine.face_metrics = {"face_detected": True, "face_count": 1}

        # 3. First Update: Starts speech timer
        self.engine.update()
        self.assertNotEqual(self.engine.continuous_speech_start_time, 0, "Speech timer should start")
        self.assertEqual(self.engine.get_mode(), "active", "Should not trigger immediately")

        # 4. Wait for Speech Threshold (0.5s)
        time.sleep(0.6)

        # 5. Second Update: Should trigger Meeting Mode
        self.engine.update()

        # Assertions
        self.assertEqual(self.engine.get_mode(), "dnd")
        self.mock_logger.log_info.assert_any_call(
            unittest.mock.ANY # "Meeting Mode Detected..."
        )

    def test_meeting_mode_no_face(self):
        """Test that meeting mode does NOT trigger if face is not detected."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = True
        self.engine.last_user_input_time = time.time() - 2.0

        # Audio: Speech detected
        self.engine.audio_analysis = {"is_speech": True}
        # Video: NO Face
        self.engine.face_metrics = {"face_detected": False}

        self.engine.update()
        time.sleep(0.6)
        self.engine.update()

        self.assertEqual(self.engine.get_mode(), "active")

    def test_meeting_mode_user_typing(self):
        """Test that meeting mode does NOT trigger if user is active (typing)."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = True
        # User typed just now
        self.engine.last_user_input_time = time.time()

        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}

        self.engine.update()
        time.sleep(0.6)
        self.engine.update()

        self.assertEqual(self.engine.get_mode(), "active")

    def test_meeting_mode_broken_speech_with_grace_period(self):
        """Test that speech timer persists during short pauses (grace period)."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = True
        self.engine.last_user_input_time = time.time() - 2.0

        # Start Speech
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}
        self.engine.update() # Timer starts
        start_time = self.engine.continuous_speech_start_time
        self.assertNotEqual(start_time, 0)

        # Short Break (less than grace period 0.3s)
        time.sleep(0.1)
        self.engine.audio_analysis = {"is_speech": False}
        self.engine.update()

        # Timer should NOT reset
        self.assertEqual(self.engine.continuous_speech_start_time, start_time)

        # Resume Speech
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.update()

        # Wait enough total time for threshold (0.5s)
        # Note: We need 0.5s from start_time. We've slept ~0.1s. Need more.
        time.sleep(0.5)
        self.engine.update()

        # Should trigger
        self.assertEqual(self.engine.get_mode(), "dnd")

    def test_meeting_mode_long_silence_resets_timer(self):
        """Test that long silence (exceeding grace period) resets the timer."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = True
        self.engine.last_user_input_time = time.time() - 2.0

        # Start Speech
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}
        self.engine.update()
        self.assertNotEqual(self.engine.continuous_speech_start_time, 0)

        # Long Break (exceeds grace period 0.3s)
        time.sleep(0.4)
        self.engine.audio_analysis = {"is_speech": False}
        self.engine.update()

        # Timer SHOULD reset
        self.assertEqual(self.engine.continuous_speech_start_time, 0)

    def test_meeting_mode_disabled_tracking(self):
        """Test that it doesn't trigger if input tracking is disabled (safety fallback)."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = False # Default state if hook fails
        self.engine.last_user_input_time = 0 # Unix Epoch (Very old)

        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}

        self.engine.update()
        time.sleep(0.6)
        self.engine.update()

        self.assertEqual(self.engine.get_mode(), "active")

    def test_meeting_mode_exit(self):
        """Test that meeting mode exits when user activity resumes."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = True
        self.engine.last_user_input_time = time.time() - 2.0

        # Trigger DND
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}
        self.engine.update() # Start timer
        time.sleep(0.6)
        self.engine.update() # Trigger

        self.assertEqual(self.engine.get_mode(), "dnd")
        self.assertTrue(self.engine.auto_dnd_active)

        # Resume User Activity (User types)
        self.engine.last_user_input_time = time.time() # Just now
        self.engine.update()

        self.assertEqual(self.engine.get_mode(), "active")
        self.assertFalse(self.engine.auto_dnd_active)

if __name__ == '__main__':
    unittest.main()
