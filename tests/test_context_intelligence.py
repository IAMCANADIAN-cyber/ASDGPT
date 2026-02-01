import pytest
from unittest.mock import MagicMock, patch, ANY
import json
import time
import sys
import collections

# Import modules to test
# We use conditional patching in the test methods/fixtures to isolate them

class TestContextIntelligence:

    @pytest.fixture
    def mock_lmm_interface(self):
        # We need to instantiate LMMInterface but mock its logger and request handling
        # We also need to patch config to avoid env/loading issues
        with patch('core.lmm_interface.config') as mock_config:
            mock_config.LOCAL_LLM_URL = "http://mock-url/v1/chat/completions"
            mock_config.LOCAL_LLM_MODEL_ID = "mock-model"
            mock_config.LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
            mock_config.LMM_CIRCUIT_BREAKER_COOLDOWN = 60

            from core.lmm_interface import LMMInterface
            lmm = LMMInterface(data_logger=MagicMock())
            return lmm

    @pytest.fixture
    def mock_logic_engine(self):
        # Similar to test_logic_engine_coverage, we need to mock dependencies
        mock_config = MagicMock()
        mock_config.DEFAULT_MODE = "active"
        mock_config.AUDIO_THRESHOLD_HIGH = 0.5
        mock_config.VIDEO_ACTIVITY_THRESHOLD_HIGH = 10.0

        mock_cv2 = MagicMock()

        with patch.dict(sys.modules, {'config': mock_config, 'cv2': mock_cv2}):
            if 'core.logic_engine' in sys.modules:
                del sys.modules['core.logic_engine']

            from core.logic_engine import LogicEngine

            with patch('core.logic_engine.DataLogger'), \
                 patch('core.logic_engine.StateEngine'), \
                 patch('core.logic_engine.InterventionEngine'):

                engine = LogicEngine()
                return engine

    @patch('requests.post')
    def test_active_window_duplication(self, mock_post, mock_lmm_interface):
        """
        Verifies that 'Active Window' is not duplicated in the prompt.
        """
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50}, "suggestion": None})}}]
        }
        mock_post.return_value = mock_response

        user_context = {
            "active_window": "VS Code - ProjectX",
            "sensor_metrics": {}
        }

        mock_lmm_interface.process_data(user_context=user_context)

        # Inspect the payload sent to requests.post
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']
        user_content = messages[1]['content']
        text_part = next(item for item in user_content if item["type"] == "text")["text"]

        # Count occurrences of "Active Window:"
        count = text_part.count("Active Window:")

        # This assertion is expected to FAIL initially (count will be 2)
        assert count == 1, f"Expected 'Active Window:' to appear once, but found {count} times.\nPrompt Content:\n{text_part}"

    def test_context_history_logic(self, mock_logic_engine):
        """
        Verifies that LogicEngine accumulates history snapshots.
        """
        # Check if context_history exists (Feature Flag/Implementation Check)
        if not hasattr(mock_logic_engine, 'context_history'):
            pytest.fail("LogicEngine does not have 'context_history' attribute yet.")

        # Simulate time passing and updates
        mock_logic_engine.context_history_interval = 0.1 # Fast interval for test

        # Update 1
        mock_logic_engine.last_history_snapshot_time = 0
        with patch('time.time', return_value=100.0):
             mock_logic_engine.update()

        assert len(mock_logic_engine.context_history) >= 1

        # Update 2 (Same time, shouldn't add)
        current_len = len(mock_logic_engine.context_history)
        with patch('time.time', return_value=100.05):
             mock_logic_engine.update()
        assert len(mock_logic_engine.context_history) == current_len

        # Update 3 (Later time, should add)
        with patch('time.time', return_value=100.2):
             mock_logic_engine.update()
        assert len(mock_logic_engine.context_history) > current_len

    @patch('requests.post')
    def test_lmm_prompt_includes_history(self, mock_post, mock_lmm_interface):
        """
        Verifies that LMMInterface injects context history into the prompt.
        """
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{}'}}] # Minimal valid JSON
        }
        mock_post.return_value = mock_response

        # Create dummy history
        history = [
            {"timestamp": 1000, "active_window": "Chrome", "mode": "active"},
            {"timestamp": 1010, "active_window": "VS Code", "mode": "active"}
        ]

        user_context = {
            "active_window": "VS Code",
            "sensor_metrics": {},
            "context_history": history
        }

        mock_lmm_interface.process_data(user_context=user_context)

        # Inspect payload
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        messages = payload['messages']
        user_content = messages[1]['content']
        text_part = next(item for item in user_content if item["type"] == "text")["text"]

        # Check for history markers
        # This assertion is expected to FAIL initially
        assert "Context History" in text_part or "Recent Activity" in text_part
        assert "Chrome" in text_part
