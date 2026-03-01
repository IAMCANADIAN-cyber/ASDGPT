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
        self.mock_window = MagicMock()

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
        self.original_blacklist = getattr(config, 'MEETING_MODE_BLACKLIST', [])

        # Set short thresholds and blacklist
        config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = 0.5
        config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = 1.0
        config.MEETING_MODE_BLACKLIST = ["YouTube", "Netflix"]

    def tearDown(self):
        # Restore config
        config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = self.original_speech_threshold
        config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = self.original_idle_threshold
        config.MEETING_MODE_BLACKLIST = self.original_blacklist

    def test_meeting_mode_suppressed_by_blacklist(self):
        """Test that meeting mode is suppressed if active window is blacklisted (e.g. YouTube)."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = True
        self.engine.last_user_input_time = time.time() - 2.0

        # Simulate Blacklisted Window
        self.mock_window.get_active_window.return_value = "YouTube - Google Chrome"

        # Simulate Meeting Conditions
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}

        # Update
        self.engine.update()
        time.sleep(0.6) # Wait for duration
        self.engine.update()

        # Assertions
        # Should remain active because YouTube is blacklisted
        self.assertEqual(self.engine.get_mode(), "active")
        # Ensure speech timer did NOT accumulate (or was reset)
        # Note: If my implementation resets it, it might be 0. If it prevents start, it is 0.
        self.assertEqual(self.engine.continuous_speech_start_time, 0)

    def test_meeting_mode_triggers_normal_app(self):
        """Test that meeting mode triggers normally for non-blacklisted apps."""
        self.engine.current_mode = "active"
        self.engine.input_tracking_enabled = True
        self.engine.last_user_input_time = time.time() - 2.0

        # Simulate Normal Window
        self.mock_window.get_active_window.return_value = "Zoom Meeting"

        # Simulate Meeting Conditions
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.face_metrics = {"face_detected": True}

        # Update - Start Timer
        self.engine.update()
        self.assertNotEqual(self.engine.continuous_speech_start_time, 0)

        # Wait
        time.sleep(0.6)

        # Update - Trigger
        self.engine.update()

        # Assertions
        self.assertEqual(self.engine.get_mode(), "dnd")

if __name__ == '__main__':
    unittest.main()
