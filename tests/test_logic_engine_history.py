import pytest
from unittest.mock import MagicMock, patch
import time
import sys
from collections import deque

class TestLogicEngineHistory:
    @pytest.fixture
    def logic_engine(self):
        # Mock config
        mock_config = MagicMock()
        mock_config.HISTORY_SIZE = 5
        mock_config.HISTORY_SAMPLE_INTERVAL = 0.1 # Fast for testing
        mock_config.DEFAULT_MODE = "active"
        mock_config.DOOM_SCROLL_THRESHOLD = 3
        mock_config.AUDIO_THRESHOLD_HIGH = 0.5
        mock_config.VIDEO_ACTIVITY_THRESHOLD_HIGH = 20.0
        mock_config.MEETING_MODE_SPEECH_DURATION_THRESHOLD = 3.0
        mock_config.MEETING_MODE_IDLE_KEYBOARD_THRESHOLD = 10.0
        mock_config.MEETING_MODE_SPEECH_GRACE_PERIOD = 2.0
        mock_config.LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
        mock_config.LMM_CIRCUIT_BREAKER_COOLDOWN = 60

        # Mock cv2 and numpy to avoid import errors
        mock_cv2 = MagicMock()
        mock_numpy = MagicMock()

        # Patch dependencies
        with patch.dict(sys.modules, {'config': mock_config, 'cv2': mock_cv2, 'numpy': mock_numpy}):
            if 'core.logic_engine' in sys.modules:
                del sys.modules['core.logic_engine']
            from core.logic_engine import LogicEngine

            with patch('core.logic_engine.DataLogger'), \
                 patch('core.logic_engine.StateEngine'):
                engine = LogicEngine()
                # Mock window sensor
                mock_ws = MagicMock()
                mock_ws.get_active_window.return_value = "TestWindow"
                engine.window_sensor = mock_ws

                # Mock state engine response
                engine.state_engine.get_state.return_value = {"focus": 100}

                # Initialize variables that might be missing due to mocking
                engine.video_activity = 0.0
                engine.audio_level = 0.0

                yield engine

    def test_history_initialization(self, logic_engine):
        assert isinstance(logic_engine.context_history, deque)
        assert logic_engine.context_history.maxlen == 5
        assert len(logic_engine.context_history) == 0

    def test_record_snapshot(self, logic_engine):
        logic_engine.video_activity = 10.5
        logic_engine.audio_level = 0.2
        logic_engine.current_mode = "active"

        # Force a record
        logic_engine.last_history_sample_time = 0
        logic_engine._record_context_snapshot()

        assert len(logic_engine.context_history) == 1
        snapshot = logic_engine.context_history[0]

        assert snapshot['active_window'] == "TestWindow"
        assert snapshot['video_activity'] == 10.5
        assert snapshot['audio_level'] == 0.2
        assert snapshot['mode'] == "active"
        assert 'timestamp' in snapshot

    def test_history_limit(self, logic_engine):
        # Fill history beyond limit
        logic_engine.last_history_sample_time = 0

        for i in range(10):
            logic_engine.video_activity = float(i)
            logic_engine._record_context_snapshot()
            # Force next sample to be valid by resetting time check
            logic_engine.last_history_sample_time = 0

        assert len(logic_engine.context_history) == 5
        # Should have last 5 items (5, 6, 7, 8, 9)
        assert logic_engine.context_history[-1]['video_activity'] == 9.0
        assert logic_engine.context_history[0]['video_activity'] == 5.0

    def test_update_calls_record(self, logic_engine):
        logic_engine.current_mode = "active"
        logic_engine.last_history_sample_time = 0

        with patch.object(logic_engine, '_record_context_snapshot', wraps=logic_engine._record_context_snapshot) as mock_record:
            logic_engine.update()
            mock_record.assert_called()
            assert len(logic_engine.context_history) == 1

    def test_prepare_lmm_data_includes_history(self, logic_engine):
        logic_engine.last_video_frame = MagicMock() # Needs to be something
        logic_engine.last_audio_chunk = MagicMock()

        # Add some history
        logic_engine.context_history.append({"test": "data"})

        data = logic_engine._prepare_lmm_data("test")

        assert "history" in data["user_context"]
        assert len(data["user_context"]["history"]) == 1
        assert data["user_context"]["history"][0]["test"] == "data"
