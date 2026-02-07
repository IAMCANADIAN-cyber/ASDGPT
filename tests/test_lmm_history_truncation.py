import unittest
from unittest.mock import MagicMock, patch
import json
import time
from core.lmm_interface import LMMInterface

class TestLMMHistoryTruncation(unittest.TestCase):
    def setUp(self):
        # Prevent actual network calls and LMM circuit breaker interference
        self.mock_logger = MagicMock()
        with patch.object(LMMInterface, 'check_connection', return_value=True):
             self.lmm_interface = LMMInterface(data_logger=self.mock_logger)
        self.lmm_interface.circuit_max_failures = 100

    @patch('requests.post')
    def test_active_window_truncation(self, mock_post):
        """Verify that overly long active_window titles are truncated."""
        long_title = "A" * 200
        user_context = {
            "active_window": long_title,
            "sensor_metrics": {},
            "current_mode": "active"
        }

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50}}'}}]
        }
        mock_post.return_value = mock_response

        self.lmm_interface.process_data(user_context=user_context)

        # Inspect the payload sent to requests.post
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        messages = payload['messages']
        user_content = messages[1]['content']
        text_part = next(item for item in user_content if item["type"] == "text")["text"]

        # Expect truncation to ~100 chars + ellipsis (length <= 103)
        # We assert it is NOT the full 200 chars
        self.assertNotIn(long_title, text_part)
        # We assert it contains the truncated version (100 chars + ...)
        truncated_expected = "A" * 100 + "..."
        self.assertIn(truncated_expected, text_part)

    @patch('requests.post')
    def test_history_truncation(self, mock_post):
        """Verify that overly long active_window titles in history are truncated."""
        long_title = "B" * 150
        history = [
            {'timestamp': time.time(), 'active_window': long_title, 'mode': 'active', 'face_detected': True}
        ]
        user_context = {
            "context_history": history,
            "sensor_metrics": {},
            "current_mode": "active"
        }

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50}}'}}]
        }
        mock_post.return_value = mock_response

        self.lmm_interface.process_data(user_context=user_context)

        # Inspect payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        messages = payload['messages']
        user_content = messages[1]['content']
        text_part = next(item for item in user_content if item["type"] == "text")["text"]

        # Expect truncation
        self.assertNotIn(long_title, text_part)
        truncated_expected = "B" * 100 + "..."
        self.assertIn(truncated_expected, text_part)

if __name__ == '__main__':
    unittest.main()
