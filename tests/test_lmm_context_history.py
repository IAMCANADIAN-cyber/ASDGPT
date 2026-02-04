import pytest
from unittest.mock import MagicMock, patch
import sys
import time

class TestLMMContextHistory:
    @pytest.fixture
    def lmm_interface(self):
        # Mock config
        mock_config = MagicMock()
        mock_config.LOCAL_LLM_URL = "http://test:1234/v1/chat/completions"
        mock_config.LOCAL_LLM_MODEL_ID = "test-model"
        mock_config.LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
        mock_config.LMM_CIRCUIT_BREAKER_COOLDOWN = 60
        mock_config.LMM_FALLBACK_ENABLED = True

        # Mock requests
        mock_requests = MagicMock()

        with patch.dict(sys.modules, {'config': mock_config, 'requests': mock_requests}):
            if 'core.lmm_interface' in sys.modules:
                del sys.modules['core.lmm_interface']
            from core.lmm_interface import LMMInterface

            with patch('core.lmm_interface.InterventionLibrary') as MockLib:
                # Configure MockLib to return a string for info
                MockLib.return_value.get_all_interventions_info.return_value = "Mock Interventions List"

                interface = LMMInterface()
                yield interface

    def test_process_data_formats_history(self, lmm_interface):
        # Mock request to intercept payload
        with patch.object(lmm_interface, '_send_request_with_retry') as mock_send:
            mock_send.return_value = {"state_estimation": {}, "suggestion": None}

            history_entry = {
                "timestamp": int(time.time()) - 30, # 30s ago
                "active_window": "VS Code",
                "video_activity": 5.5,
                "audio_level": 0.01,
                "mode": "active"
            }

            user_context = {
                "history": [history_entry],
                "sensor_metrics": {}
            }

            lmm_interface.process_data(video_data="fake", audio_data=[], user_context=user_context)

            # Verify payload
            call_args = mock_send.call_args
            payload = call_args[0][0]

            # Find the user message
            user_msg = next(msg for msg in payload['messages'] if msg['role'] == 'user')
            text_part = next(part for part in user_msg['content'] if part['type'] == 'text')
            text = text_part['text']

            assert "Recent Context History" in text
            assert "VS Code" in text
            assert "30s ago" in text
            assert "Act: 5.5" in text

    def test_process_data_no_history(self, lmm_interface):
        with patch.object(lmm_interface, '_send_request_with_retry') as mock_send:
            mock_send.return_value = {"state_estimation": {}, "suggestion": None}

            user_context = {
                "history": [],
                "sensor_metrics": {}
            }

            lmm_interface.process_data(video_data="fake", audio_data=[], user_context=user_context)

            payload = mock_send.call_args[0][0]
            user_msg = next(msg for msg in payload['messages'] if msg['role'] == 'user')
            text = next(part for part in user_msg['content'] if part['type'] == 'text')['text']

            assert "Recent Context History" not in text

    def test_process_data_handles_malformed_history(self, lmm_interface):
        with patch.object(lmm_interface, '_send_request_with_retry') as mock_send:
            mock_send.return_value = {}

            # History is not a list
            user_context = {
                "history": "invalid",
                "sensor_metrics": {}
            }

            # Should not crash
            lmm_interface.process_data(video_data="fake", audio_data=[], user_context=user_context)

            payload = mock_send.call_args[0][0]
            user_msg = next(msg for msg in payload['messages'] if msg['role'] == 'user')
            text = next(part for part in user_msg['content'] if part['type'] == 'text')['text']

            assert "Recent Context History" not in text
