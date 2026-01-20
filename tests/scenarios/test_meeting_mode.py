import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.logic_engine import LogicEngine
import config

class TestMeetingMode(unittest.TestCase):
    def setUp(self):
        # Ensure config defaults are set for test
        config.MEETING_MODE_ENABLED = True
        config.MEETING_SPEECH_DURATION = 45
        config.MEETING_FACE_DURATION = 30
        config.MEETING_IDLE_DURATION = 30

        # Mock logger to avoid writing to file
        mock_logger = MagicMock()

        self.logic_engine = LogicEngine(logger=mock_logger)
        # Mock sensors state
        self.logic_engine.audio_analysis = {"is_speech": False}
        self.logic_engine.face_metrics = {"face_detected": False}

    @patch('time.time')
    def test_meeting_mode_trigger(self, mock_time):
        # Start time
        start_time = 1000.0
        mock_time.return_value = start_time

        # Initialize
        self.logic_engine.register_user_input() # User active at start
        self.logic_engine.set_mode("active")

        # 1. Start Speech and Face detection
        self.logic_engine.audio_analysis = {"is_speech": True}
        self.logic_engine.face_metrics = {"face_detected": True}

        # Update 1: Session starts
        self.logic_engine.update()
        self.assertEqual(self.logic_engine.speech_session_start, start_time)
        self.assertEqual(self.logic_engine.face_session_start, start_time)

        # 2. Advance time by 44s (Just under 45s threshold)
        current_time = start_time + 44.0
        mock_time.return_value = current_time

        # User input is old (44s > 30s), so Idle is True.
        # Face is old (44s > 30s), so Face is True.
        # Speech is 44s < 45s, so Speech condition NOT met.

        self.logic_engine.update()
        self.assertEqual(self.logic_engine.get_mode(), "active")

        # 3. Advance to 46s
        current_time = start_time + 46.0
        mock_time.return_value = current_time

        self.logic_engine.update()
        self.assertEqual(self.logic_engine.get_mode(), "dnd")

    @patch('time.time')
    def test_meeting_mode_interrupted_by_input(self, mock_time):
        # Start time
        start_time = 1000.0
        mock_time.return_value = start_time

        self.logic_engine.register_user_input()
        self.logic_engine.set_mode("active")

        # Start Speech and Face
        self.logic_engine.audio_analysis = {"is_speech": True}
        self.logic_engine.face_metrics = {"face_detected": True}
        self.logic_engine.update()

        # Advance 40s
        mock_time.return_value = start_time + 40.0
        self.logic_engine.update()

        # User types!
        self.logic_engine.register_user_input() # Updates last_user_input_time to 1040.0

        # Advance to 50s (Total duration 50s)
        # Speech duration = 50s (> 45s)
        # Face duration = 50s (> 30s)
        # Idle duration = 50s - 40s = 10s (< 30s) -> FAIL
        mock_time.return_value = start_time + 50.0

        self.logic_engine.update()
        self.assertEqual(self.logic_engine.get_mode(), "active")

    @patch('time.time')
    def test_meeting_mode_interrupted_by_silence(self, mock_time):
        start_time = 1000.0
        mock_time.return_value = start_time

        self.logic_engine.register_user_input()
        self.logic_engine.set_mode("active")

        # Start Speech
        self.logic_engine.audio_analysis = {"is_speech": True}
        self.logic_engine.face_metrics = {"face_detected": True}
        self.logic_engine.update()

        # Advance 20s
        mock_time.return_value = start_time + 20.0
        self.logic_engine.update()

        # Silence for 6s (Break session)
        self.logic_engine.audio_analysis = {"is_speech": False}
        mock_time.return_value = start_time + 26.0
        self.logic_engine.update()
        self.assertEqual(self.logic_engine.speech_session_start, 0)

        # Resume Speech
        self.logic_engine.audio_analysis = {"is_speech": True}
        mock_time.return_value = start_time + 27.0
        self.logic_engine.update()
        self.assertEqual(self.logic_engine.speech_session_start, start_time + 27.0) # New session

        # Advance to 60s total (New session is only 33s)
        mock_time.return_value = start_time + 60.0
        self.logic_engine.update()
        self.assertEqual(self.logic_engine.get_mode(), "active")

if __name__ == '__main__':
    unittest.main()
