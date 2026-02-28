import time
import unittest
from unittest.mock import MagicMock
from core.logic_engine import LogicEngine
import config

class TestMeetingModeBlacklist(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_window = MagicMock()
        self.mock_lmm = MagicMock()

        # Instantiate LogicEngine with mocks
        self.engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            window_sensor=self.mock_window,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm
        )

        # Override config thresholds for faster testing
        self.original_speech_threshold = getattr(config, 'MEETING_MODE_SPEECH_DURATION_THRESHOLD', 3.0)
        self.original_idle_threshold = getattr(config, 'MEETING_MODE_IDLE_KEYBOARD_THRESHOLD', 10.0)
        self.original_grace_period = getattr(config, 'MEETING_MODE_SPEECH_GRACE_PERIOD', 2.0)
        self.original_blacklist = getattr(config, 'MEETING_MODE_BLACKLIST', [])

        # Set short thresholds
        config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = 0.5
        config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = 1.0
        config.MEETING_MODE_SPEECH_GRACE_PERIOD = 0.2
        config.MEETING_MODE_BLACKLIST = ["YouTube", "Netflix", "VLC"]

    def tearDown(self):
        # Restore config
        config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = self.original_speech_threshold
        config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = self.original_idle_threshold
        config.MEETING_MODE_SPEECH_GRACE_PERIOD = self.original_grace_period
        config.MEETING_MODE_BLACKLIST = self.original_blacklist

    def test_meeting_mode_suppressed_by_blacklist(self):
        """Test that meeting mode does NOT trigger if the active window is blacklisted."""
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
        # Window: Blacklisted (YouTube)
        self.mock_window.get_active_window.return_value = "Awesome Video - YouTube - Google Chrome"

        # 3. First Update: Starts speech timer
        self.engine.update()
        self.assertNotEqual(self.engine.continuous_speech_start_time, 0, "Speech timer should start")
        self.assertEqual(self.engine.get_mode(), "active", "Should not trigger immediately")

        # 4. Wait for Speech Threshold (0.5s)
        time.sleep(0.6)

        # 5. Second Update: Should normally trigger Meeting Mode, but suppressed due to blacklist
        self.engine.update()

        # Assertions
        self.mock_window.get_active_window.assert_called_with(sanitize=False)
        self.assertEqual(self.engine.get_mode(), "active", "Should remain active due to blacklist")

    def test_meeting_mode_triggers_if_not_blacklisted(self):
        """Test that meeting mode DOES trigger if the active window is not blacklisted."""
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
        # Window: Not blacklisted (Zoom)
        self.mock_window.get_active_window.return_value = "Zoom Meeting"

        # 3. First Update: Starts speech timer
        self.engine.update()
        self.assertNotEqual(self.engine.continuous_speech_start_time, 0, "Speech timer should start")

        # 4. Wait for Speech Threshold (0.5s)
        time.sleep(0.6)

        # 5. Second Update: Should trigger Meeting Mode
        self.engine.update()

        # Assertions
        self.mock_window.get_active_window.assert_called_with(sanitize=False)
        self.assertEqual(self.engine.get_mode(), "dnd", "Should switch to DND as Zoom is not blacklisted")

if __name__ == '__main__':
    unittest.main()
