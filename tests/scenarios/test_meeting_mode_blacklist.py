import time
import unittest
from unittest.mock import MagicMock, patch
from core.logic_engine import LogicEngine
import config

class TestMeetingModeBlacklist(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_lmm = MagicMock()
        self.mock_window_sensor = MagicMock()

        self.engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm,
            window_sensor=self.mock_window_sensor
        )

        self.original_speech_threshold = getattr(config, 'MEETING_MODE_SPEECH_DURATION_THRESHOLD', 3.0)
        self.original_idle_threshold = getattr(config, 'MEETING_MODE_IDLE_KEYBOARD_THRESHOLD', 10.0)
        self.original_grace_period = getattr(config, 'MEETING_MODE_SPEECH_GRACE_PERIOD', 2.0)
        self.original_blacklist = getattr(config, 'MEETING_MODE_BLACKLIST', [])

        config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = 0.5
        config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = 1.0
        config.MEETING_MODE_SPEECH_GRACE_PERIOD = 0.2
        config.MEETING_MODE_BLACKLIST = ["YouTube", "Netflix", "VLC"]

    def tearDown(self):
        config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = self.original_speech_threshold
        config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = self.original_idle_threshold
        config.MEETING_MODE_SPEECH_GRACE_PERIOD = self.original_grace_period
        config.MEETING_MODE_BLACKLIST = self.original_blacklist

    def test_meeting_mode_suppressed_by_blacklist(self):
        """Test that meeting mode does NOT trigger if active window matches blacklist."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = True
        self.engine.last_user_input_time = time.time() - 2.0

        # Audio: Speech detected
        self.engine.audio_analysis = {"is_speech": True, "rms": 0.5}
        # Video: Face detected
        self.engine.face_metrics = {"face_detected": True, "face_count": 1}
        # Window: YouTube is active (case-insensitive check)
        self.mock_window_sensor.get_active_window.return_value = "Watching cat videos - YouTube"

        self.engine.update() # First Update: Timer normally starts
        time.sleep(0.6) # Wait for duration threshold (0.5s)
        self.engine.update() # Second Update: Should normally trigger

        # Should remain active
        self.assertEqual(self.engine.get_mode(), "active", "Should be suppressed by blacklist")

    def test_meeting_mode_triggers_normally(self):
        """Test that meeting mode DOES trigger if active window is not in blacklist."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = True
        self.engine.last_user_input_time = time.time() - 2.0

        self.engine.audio_analysis = {"is_speech": True, "rms": 0.5}
        self.engine.face_metrics = {"face_detected": True, "face_count": 1}
        self.mock_window_sensor.get_active_window.return_value = "Zoom Meeting"

        self.engine.update()
        time.sleep(0.6)
        self.engine.update()

        # Should be dnd
        self.assertEqual(self.engine.get_mode(), "dnd", "Should trigger normally")

if __name__ == '__main__':
    unittest.main()
