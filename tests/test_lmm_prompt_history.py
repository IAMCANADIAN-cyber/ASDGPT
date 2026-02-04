import unittest
from unittest.mock import MagicMock, patch
import time
from core.lmm_interface import LMMInterface

class TestLMMPromptHistory(unittest.TestCase):
    def setUp(self):
        self.lmm_interface = LMMInterface()
        # Mock requests to avoid network
        self.patcher = patch('requests.post')
        self.mock_post = self.patcher.start()

        # Mock response to be valid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50}}'}}],
            "usage": {}
        }
        self.mock_post.return_value = mock_response

    def tearDown(self):
        self.patcher.stop()

    def test_process_data_formats_history(self):
        # Create user context with history
        history = [
            {"timestamp": 1600000000, "mode": "active", "active_window": "Window A"},
            {"timestamp": 1600000010, "mode": "active", "active_window": "Window B"},
        ]
        user_context = {
            "history": history,
            "active_window": "Window B",
            "current_mode": "active",
            "sensor_metrics": {}
        }

        self.lmm_interface.process_data(video_data="fake_base64", user_context=user_context)

        # Verify the prompt content
        call_args = self.mock_post.call_args
        payload = call_args[1]['json']
        messages = payload['messages']
        user_message_parts = messages[1]['content']
        text_part = user_message_parts[0]['text']

        print(f"DEBUG: Prompt Text:\n{text_part}")

        self.assertIn("Context History (Newest Last, ~10s interval):", text_part)
        self.assertIn("Window: Window A", text_part)
        self.assertIn("Window: Window B", text_part)
        # Verify timestamp formatting (just checking if some time format is present)
        # 1600000000 is 2020-09-13 12:26:40 UTC. Localtime might vary, but "Window A" should be prefixed by time.
        self.assertRegex(text_part, r"\[\d{2}:\d{2}:\d{2}\] Mode: active, Window: Window A")

if __name__ == '__main__':
    unittest.main()
