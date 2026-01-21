import time
import pytest
from unittest.mock import MagicMock, patch
import config
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface

# Mock config constants for faster testing
config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = 0.5
config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = 1.0

class TestMeetingMode:
    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def logic_engine(self, mock_logger):
        lmm = MagicMock(spec=LMMInterface)
        engine = LogicEngine(logger=mock_logger, lmm_interface=lmm)

        # Manually enable input tracking as if main.py succeeded
        engine.input_tracking_enabled = True

        # Override config values in instance
        engine.meeting_mode_speech_threshold = 0.5
        engine.meeting_mode_idle_threshold = 1.0

        return engine

    @patch('time.time')
    def test_meeting_mode_trigger_basic(self, mock_time, logic_engine):
        """
        Verifies that Meeting Mode is triggered when:
        1. Continuous speech is detected > threshold
        2. Face is detected
        3. User is idle (no keyboard) > threshold
        """
        start_time = 1000.0
        mock_time.return_value = start_time

        # Initial state
        assert logic_engine.current_mode == "active"

        # Setup: User is idle (last input was at 998.0, so 2.0s ago)
        logic_engine.last_user_input_time = start_time - 2.0

        # Setup: Mock Sensor Data (Face detected, Speech detected)
        logic_engine.face_metrics = {"face_detected": True, "face_count": 1}
        logic_engine.audio_analysis = {"is_speech": True}

        # 1. First Update: Starts speech timer
        logic_engine.update()
        assert logic_engine.meeting_mode_speech_start_time == start_time
        assert logic_engine.current_mode == "active"

        # 2. Advance time by 0.6s (past 0.5s threshold)
        mock_time.return_value = start_time + 0.6

        # 3. Second Update: Should trigger
        logic_engine.update()

        assert logic_engine.current_mode == "dnd"

        # Verify log message matches roughly
        # We expect idle time to be 2.6s (2.0 initial + 0.6 elapsed)
        # We expect speech duration to be 0.6s
        # exact string match might still vary on float formatting, so we check partial
        found = False
        for call in logic_engine.logger.log_info.call_args_list:
            msg = call[0][0]
            if "Meeting Mode Detected" in msg and "Switching to DND" in msg:
                found = True
                break
        assert found, "Did not find expected Meeting Mode log message"

    @patch('time.time')
    def test_meeting_mode_prevented_by_input(self, mock_time, logic_engine):
        """
        Verifies that recent keyboard input prevents Meeting Mode even if speaking.
        """
        start_time = 1000.0
        mock_time.return_value = start_time

        logic_engine.face_metrics = {"face_detected": True}
        logic_engine.audio_analysis = {"is_speech": True}

        # User just typed
        logic_engine.register_user_input() # updates last_user_input_time to 1000.0

        logic_engine.update() # Start speech timer

        # Advance time by 0.6s
        mock_time.return_value = start_time + 0.6
        logic_engine.update() # Check trigger

        # Should NOT trigger because idle time (0.6s) < threshold (1.0s)
        assert logic_engine.current_mode == "active"

    @patch('time.time')
    def test_meeting_mode_prevented_by_no_face(self, mock_time, logic_engine):
        """
        Verifies that lack of face detection prevents Meeting Mode.
        """
        start_time = 1000.0
        mock_time.return_value = start_time

        logic_engine.last_user_input_time = start_time - 2.0
        logic_engine.face_metrics = {"face_detected": False}
        logic_engine.audio_analysis = {"is_speech": True}

        logic_engine.update()

        mock_time.return_value = start_time + 0.6
        logic_engine.update()

        assert logic_engine.current_mode == "active"

    @patch('time.time')
    def test_meeting_mode_prevented_by_intermittent_speech(self, mock_time, logic_engine):
        """
        Verifies that speech timer resets if speech stops.
        """
        start_time = 1000.0
        mock_time.return_value = start_time

        logic_engine.last_user_input_time = start_time - 2.0
        logic_engine.face_metrics = {"face_detected": True}

        # Speech starts
        logic_engine.audio_analysis = {"is_speech": True}
        logic_engine.update()
        assert logic_engine.meeting_mode_speech_start_time == start_time

        # Advance 0.3s
        mock_time.return_value = start_time + 0.3

        # Speech stops
        logic_engine.audio_analysis = {"is_speech": False}
        logic_engine.update()
        assert logic_engine.meeting_mode_speech_start_time == 0

        # Advance 0.1s
        mock_time.return_value = start_time + 0.4

        # Speech starts again
        logic_engine.audio_analysis = {"is_speech": True}
        logic_engine.update()
        assert logic_engine.meeting_mode_speech_start_time == start_time + 0.4 # New start time

        # Not enough time accumulated yet
        assert logic_engine.current_mode == "active"

    @patch('time.time')
    def test_meeting_mode_requires_tracking_enabled(self, mock_time, logic_engine):
        """
        Verifies that logic is disabled if input_tracking_enabled is False.
        """
        start_time = 1000.0
        mock_time.return_value = start_time

        logic_engine.input_tracking_enabled = False
        logic_engine.last_user_input_time = start_time - 2.0
        logic_engine.face_metrics = {"face_detected": True}
        logic_engine.audio_analysis = {"is_speech": True}

        logic_engine.update()

        mock_time.return_value = start_time + 0.6
        logic_engine.update()

        assert logic_engine.current_mode == "active"
