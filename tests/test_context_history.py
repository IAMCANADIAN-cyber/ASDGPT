import pytest
from unittest.mock import MagicMock, patch
import time
import sys
from collections import deque
import core.logic_engine
import core.lmm_interface
import config

class TestContextHistory:

    @pytest.fixture
    def mock_lmm(self):
        lmm = MagicMock()
        lmm.process_data.return_value = {"state_estimation": {}, "suggestion": None}
        return lmm

    @pytest.fixture
    def logic_engine(self, mock_lmm):
        # We don't need to patch sys.modules or re-import.
        # Just patch the config attributes that LogicEngine reads during __init__ or update.

        with patch('core.logic_engine.config.HISTORY_SAMPLE_INTERVAL', 1), \
             patch('core.logic_engine.config.DEFAULT_MODE', 'active'), \
             patch('core.logic_engine.DataLogger'), \
             patch('core.logic_engine.StateEngine'):

            engine = core.logic_engine.LogicEngine(lmm_interface=mock_lmm)
            # Ensure the instance variable is set correctly (it reads from config in __init__)
            # Since we patched config before init, it should be 1.
            yield engine

    def test_history_accumulation(self, logic_engine):
        # Initial state
        assert len(logic_engine.context_history) == 0

        # Simulate time passing and update
        current_time = time.time()
        logic_engine.last_history_update_time = current_time - 2.0 # Force update
        logic_engine.current_mode = "active"
        logic_engine.audio_level = 0.5
        logic_engine.video_activity = 10.0

        # Ensure lock is not an issue (it shouldn't be in single thread)
        logic_engine.update()

        assert len(logic_engine.context_history) == 1
        snap = logic_engine.context_history[0]
        assert snap['mode'] == "active"
        assert snap['audio_level'] == "0.50"

        # Another update
        logic_engine.last_history_update_time = time.time() - 2.0
        logic_engine.current_mode = "dnd" # Changed to a VALID mode
        logic_engine.update()

        assert len(logic_engine.context_history) == 2
        assert logic_engine.context_history[1]['mode'] == "dnd"

    def test_history_sliding_window(self, logic_engine):
        logic_engine.context_history = deque(maxlen=3) # Override for quicker test

        for i in range(5):
            logic_engine.last_history_update_time = time.time() - 2.0
            logic_engine.current_mode = "active" # Keep valid mode
            # Vary something else to verify correct snapshot
            logic_engine.audio_level = float(i)
            logic_engine.update()

        assert len(logic_engine.context_history) == 3
        # Should have [2, 3, 4]
        assert logic_engine.context_history[0]['audio_level'] == "2.00"
        assert logic_engine.context_history[2]['audio_level'] == "4.00"

    def test_prepare_lmm_data_includes_history(self, logic_engine):
        # Populate history
        logic_engine.context_history.append({"mock": "data"})

        # Mock sensors to allow data preparation
        # LogicEngine checks for None
        logic_engine.last_video_frame = "mock_frame_data"
        logic_engine.last_audio_chunk = None

        # Patch cv2.imencode and base64 to avoid numpy/cv2 issues
        with patch('cv2.imencode', return_value=(True, b'data')), \
             patch('base64.b64encode', return_value=b'encoded'):
                 data = logic_engine._prepare_lmm_data("test")

        assert "history" in data["user_context"]
        assert len(data["user_context"]["history"]) == 1
        assert data["user_context"]["history"][0]["mock"] == "data"


class TestLMMInterfaceHistory:
    @pytest.fixture
    def lmm_interface(self):
        # Patch config attributes used in LMMInterface __init__
        with patch('core.lmm_interface.config.LOCAL_LLM_URL', "http://test/v1/chat/completions"), \
             patch('core.lmm_interface.config.LMM_CIRCUIT_BREAKER_MAX_FAILURES', 5), \
             patch('core.lmm_interface.config.LMM_CIRCUIT_BREAKER_COOLDOWN', 60), \
             patch('core.lmm_interface.config.LMM_FALLBACK_ENABLED', False):

             return core.lmm_interface.LMMInterface()

    @patch('requests.post')
    def test_process_data_formats_history(self, mock_post, lmm_interface):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
        mock_post.return_value = mock_response

        # Create dummy history
        history = [
            {"timestamp": time.time() - 20, "mode": "active", "active_window": "Work", "video_activity": 5.0, "face_detected": True},
            {"timestamp": time.time() - 10, "mode": "snoozed", "active_window": "Game", "video_activity": 0.0, "face_detected": False}
        ]

        user_context = {
            "history": history,
            "sensor_metrics": {}
        }

        lmm_interface.process_data(user_context=user_context)

        # Inspect the prompt sent
        assert mock_post.called
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']
        user_text = next(m for m in messages[1]['content'] if m['type'] == 'text')['text']

        # print(user_text) # Debug

        assert "Recent History" in user_text
        assert "[20s ago] Mode: active" in user_text
        assert "Window: Work" in user_text
        assert "[10s ago] Mode: snoozed" in user_text
