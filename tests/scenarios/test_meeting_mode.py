import time
import unittest
from unittest.mock import MagicMock, patch
from core.logic_engine import LogicEngine
import config

class TestMeetingMode(unittest.TestCase):
    def setUp(self):
        # Create a mock logger
        self.mock_logger = MagicMock()

        # Initialize LogicEngine with mock logger
        self.logic_engine = LogicEngine(logger=self.mock_logger)

        # Set config thresholds for testing (shorten them)
        self.logic_engine.meeting_speech_start_time = 0
        self.logic_engine.meeting_face_start_time = 0
        self.logic_engine.last_user_input_time = time.time() # Start as active
        self.logic_engine.activity_tracking_enabled = True # Simulate hook success

        # Patch config values dynamically if possible, or we rely on logic engine using getattr
        # Since logic engine uses getattr(config, ...), we can patch config
        self.patcher = patch('core.logic_engine.config')
        self.mock_config = self.patcher.start()

        # Set default values for mock config to match actual defaults roughly
        self.mock_config.DEFAULT_MODE = "active"
        self.mock_config.SNOOZE_DURATION = 3600
        self.mock_config.AUDIO_THRESHOLD_HIGH = 0.5
        self.mock_config.VIDEO_ACTIVITY_THRESHOLD_HIGH = 20.0

        # Set Meeting thresholds low for testing
        self.mock_config.MEETING_SPEECH_DURATION = 2
        self.mock_config.MEETING_FACE_DURATION = 2
        self.mock_config.MEETING_IDLE_DURATION = 2

    def tearDown(self):
        self.patcher.stop()

    def test_meeting_mode_trigger(self):
        """Test that meeting mode triggers when conditions are met."""

        # 1. Start in active mode
        self.logic_engine.set_mode("active")
        self.assertEqual(self.logic_engine.get_mode(), "active")

        # 2. Simulate User Idle (time travel)
        start_time = time.time()
        self.logic_engine.last_user_input_time = start_time - 5 # 5 seconds idle (Threshold is 2)

        # 3. Simulate Continuous Face & Speech
        # We need to pump update() a few times with sensor data

        # Iteration 1: Face detected, Speech detected
        self.logic_engine.face_metrics = {"face_detected": True}
        self.logic_engine.audio_analysis = {"is_speech": True}

        # We need to manipulate time inside logic engine, or wait.
        # Patching time.time is safer for deterministic tests.
        with patch('time.time') as mock_time:
            mock_time.return_value = start_time
            self.logic_engine.update()
            # Should have started timers
            self.assertGreater(self.logic_engine.meeting_speech_start_time, 0)
            self.assertGreater(self.logic_engine.meeting_face_start_time, 0)

            # Iteration 2: 3 seconds later (exceeds threshold of 2)
            mock_time.return_value = start_time + 3
            self.logic_engine.update()

            # Should now be in DND
            self.assertEqual(self.logic_engine.get_mode(), "dnd")
            self.mock_logger.log_info.assert_any_call(
                unittest.mock.ANY
            )

    def test_meeting_mode_interrupted_by_input(self):
        """Test that meeting mode doesn't trigger if user is typing."""
        self.logic_engine.set_mode("active")

        start_time = time.time()
        self.logic_engine.last_user_input_time = start_time # Just typed

        self.logic_engine.face_metrics = {"face_detected": True}
        self.logic_engine.audio_analysis = {"is_speech": True}

        with patch('time.time') as mock_time:
            mock_time.return_value = start_time
            self.logic_engine.update()

            mock_time.return_value = start_time + 3 # Threshold passed for speech/face
            self.logic_engine.update()

            # Reset
            self.logic_engine.set_mode("active")
            self.logic_engine.meeting_speech_start_time = 0

            # Scenario: User keeps typing
            self.logic_engine.last_user_input_time = start_time + 3 # Updated timestamp
            self.logic_engine.update()

            self.assertEqual(self.logic_engine.get_mode(), "active")

    def test_meeting_mode_interrupted_by_silence(self):
        """Test that speech gaps break the trigger."""
        self.logic_engine.set_mode("active")
        start_time = time.time()
        self.logic_engine.last_user_input_time = start_time - 5

        with patch('time.time') as mock_time:
            mock_time.return_value = start_time

            # Speech starts
            self.logic_engine.audio_analysis = {"is_speech": True}
            self.logic_engine.face_metrics = {"face_detected": True}
            self.logic_engine.update()

            # Silence for 3 seconds (Grace period is 2s)
            mock_time.return_value = start_time + 3
            self.logic_engine.audio_analysis = {"is_speech": False}
            self.logic_engine.update()

            # Speech start time should be reset
            self.assertEqual(self.logic_engine.meeting_speech_start_time, 0)

            # 1 second later speech resumes
            mock_time.return_value = start_time + 4
            self.logic_engine.audio_analysis = {"is_speech": True}
            self.logic_engine.update()

            # New start time set
            self.assertEqual(self.logic_engine.meeting_speech_start_time, start_time + 4)

            # Not DND yet
            self.assertEqual(self.logic_engine.get_mode(), "active")

    def test_meeting_mode_disabled_if_tracking_fails(self):
        """Test that meeting mode is disabled if keyboard tracking is off."""
        # 1. Start in active mode
        self.logic_engine.set_mode("active")

        # 2. Simulate User Idle
        start_time = time.time()
        self.logic_engine.last_user_input_time = start_time - 100 # Very old

        # 3. Simulate Tracking Failure
        self.logic_engine.activity_tracking_enabled = False

        # 4. Simulate Meeting Conditions
        self.logic_engine.face_metrics = {"face_detected": True}
        self.logic_engine.audio_analysis = {"is_speech": True}

        with patch('time.time') as mock_time:
            mock_time.return_value = start_time
            self.logic_engine.update()

            # Advance time
            mock_time.return_value = start_time + 5
            self.logic_engine.update()

            # Should NOT be in DND
            self.assertEqual(self.logic_engine.get_mode(), "active")
