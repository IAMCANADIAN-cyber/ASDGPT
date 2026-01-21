import unittest
from unittest.mock import MagicMock, patch
import time
import numpy as np
from core.logic_engine import LogicEngine
import config

class TestMeetingMode(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_lmm = MagicMock()

        # Setup mock sensors
        self.mock_audio.analyze_chunk.return_value = {"rms": 0.1, "is_speech": False}
        self.mock_video.process_frame.return_value = {"face_detected": False, "face_count": 0, "video_activity": 0.0}

        # Instantiate LogicEngine
        self.logic_engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm
        )

        # Explicitly enable tracking for test
        self.logic_engine.input_tracking_enabled = True

        # Shorten thresholds for testing
        self.logic_engine.meeting_mode_speech_threshold = 0.5  # 0.5 seconds
        self.logic_engine.meeting_mode_idle_threshold = 1.0    # 1.0 second

    def test_meeting_mode_trigger(self):
        """
        Verify that meeting mode is triggered when:
        1. Speech is continuous for > threshold
        2. Face is detected
        3. User input is idle for > threshold
        """

        # 1. Simulate Idle User
        # Set last input to 2 seconds ago (idle threshold is 1.0s)
        self.logic_engine.last_user_input_time = time.time() - 2.0

        # 2. Simulate Face Detected
        self.logic_engine.face_metrics = {"face_detected": True, "face_count": 1}

        # 3. Simulate Continuous Speech
        # LogicEngine.update() checks time.time(), so we need to loop with sleep or patch time.
        # Patching time is cleaner.

        start_time = time.time()

        with patch('time.time') as mock_time:
            # T = 0: Speech starts
            mock_time.return_value = start_time
            self.logic_engine.audio_analysis = {"rms": 0.5, "is_speech": True}
            self.logic_engine.update()

            # Check internal state
            self.assertEqual(self.logic_engine.speech_start_time, start_time)
            self.assertEqual(self.logic_engine.get_mode(), "active") # Not yet triggered

            # T = 0.6: Speech continues (> 0.5 threshold)
            mock_time.return_value = start_time + 0.6
            self.logic_engine.update()

            # Should have triggered DND
            self.assertEqual(self.logic_engine.get_mode(), "dnd")
            self.mock_logger.log_info.assert_any_call(
                unittest.mock.ANY # "Meeting Mode Detected..."
            )

    def test_meeting_mode_no_face(self):
        """Verify DND is NOT triggered if no face is detected."""
        self.logic_engine.last_user_input_time = time.time() - 2.0
        self.logic_engine.face_metrics = {"face_detected": False, "face_count": 0}

        start_time = time.time()
        with patch('time.time') as mock_time:
            mock_time.return_value = start_time
            self.logic_engine.audio_analysis = {"rms": 0.5, "is_speech": True}
            self.logic_engine.update()

            mock_time.return_value = start_time + 0.6
            self.logic_engine.update()

            self.assertEqual(self.logic_engine.get_mode(), "active")

    def test_meeting_mode_active_input(self):
        """Verify DND is NOT triggered if user is typing."""
        # User typed just now
        self.logic_engine.last_user_input_time = time.time()
        self.logic_engine.face_metrics = {"face_detected": True, "face_count": 1}

        start_time = time.time()
        with patch('time.time') as mock_time:
            mock_time.return_value = start_time
            self.logic_engine.audio_analysis = {"rms": 0.5, "is_speech": True}
            self.logic_engine.update()

            mock_time.return_value = start_time + 0.6
            self.logic_engine.update()

            self.assertEqual(self.logic_engine.get_mode(), "active")

    def test_meeting_mode_not_continuous_speech(self):
        """Verify DND is NOT triggered if speech breaks."""
        self.logic_engine.last_user_input_time = time.time() - 2.0
        self.logic_engine.face_metrics = {"face_detected": True, "face_count": 1}

        start_time = time.time()
        with patch('time.time') as mock_time:
            # T=0: Speech
            mock_time.return_value = start_time
            self.logic_engine.audio_analysis = {"rms": 0.5, "is_speech": True}
            self.logic_engine.update()

            # T=0.3: Silence (Reset)
            mock_time.return_value = start_time + 0.3
            self.logic_engine.audio_analysis = {"rms": 0.0, "is_speech": False}
            self.logic_engine.update()
            self.assertEqual(self.logic_engine.speech_start_time, 0)

            # T=0.4: Speech again
            mock_time.return_value = start_time + 0.4
            self.logic_engine.audio_analysis = {"rms": 0.5, "is_speech": True}
            self.logic_engine.update()

            # T=0.8: Total elapsed 0.8, but continuous only 0.4
            mock_time.return_value = start_time + 0.8
            self.logic_engine.update()

            self.assertEqual(self.logic_engine.get_mode(), "active")

if __name__ == '__main__':
    unittest.main()
