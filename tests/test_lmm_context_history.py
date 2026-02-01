import pytest
import time
from unittest.mock import MagicMock, patch
from collections import deque
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface
import config

class TestContextHistory:
    @pytest.fixture
    def mock_deps(self):
        return {
            "audio": MagicMock(),
            "video": MagicMock(),
            "window": MagicMock(),
            "logger": MagicMock(),
            "lmm": MagicMock()
        }

    def test_logic_engine_history_accumulation(self, mock_deps):
        engine = LogicEngine(
            audio_sensor=mock_deps["audio"],
            video_sensor=mock_deps["video"],
            window_sensor=mock_deps["window"],
            logger=mock_deps["logger"],
            lmm_interface=mock_deps["lmm"]
        )

        # Verify init
        assert isinstance(engine.context_history, deque)
        assert engine.context_history.maxlen == 10
        assert len(engine.context_history) == 0

        # Simulate data preparation triggers
        # We need to set some dummy data so _prepare_lmm_data doesn't return None
        engine.last_video_frame = "dummy_frame"

        # mocking window sensor
        mock_deps["window"].get_active_window.return_value = "Test App"

        # Run 15 times to overflow buffer
        for i in range(15):
            mock_deps["window"].get_active_window.return_value = f"App {i}"
            payload = engine._prepare_lmm_data(trigger_reason="test")
            assert payload is not None

            # Check context history in payload
            history = payload["user_context"]["context_history"]
            assert len(history) == min(i + 1, 10)
            assert history[-1]["active_window"] == f"App {i}"

        # Verify max length in engine
        assert len(engine.context_history) == 10
        # Buffer should contain [5, 6, ..., 14]
        # index 0 should be App 5
        assert engine.context_history[0]["active_window"] == "App 5"
        assert engine.context_history[-1]["active_window"] == "App 14"

    def test_lmm_interface_prompt_injection(self):
        lmm_interface = LMMInterface(data_logger=MagicMock())

        # Mock _send_request_with_retry to capture the payload
        with patch.object(lmm_interface, '_send_request_with_retry') as mock_send:
            mock_send.return_value = {"state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50}}

            # Create a user context with history
            history = []
            for i in range(3):
                history.append({
                    "timestamp": time.time() - (10 - i),
                    "mode": "active",
                    "active_window": f"App {i}",
                    "face_detected": True,
                    "video_activity": 1.5
                })

            user_context = {
                "current_mode": "active",
                "trigger_reason": "test",
                "active_window": "Current App",
                "context_history": history,
                "sensor_metrics": {}
            }

            lmm_interface.process_data(video_data="base64data", user_context=user_context)

            # Check call args
            assert mock_send.called
            call_args = mock_send.call_args
            payload = call_args[0][0] # First arg of the call

            messages = payload["messages"]
            user_content = messages[1]["content"] # 0 is system, 1 is user

            # Find text part
            text_part = next(p for p in user_content if p["type"] == "text")["text"]

            # Debug output if assertion fails
            print(f"Generated Text Part: {text_part}")

            assert "Recent Context History" in text_part
            assert "Win: App 0" in text_part
            assert "Win: App 1" in text_part
            assert "Win: App 2" in text_part
