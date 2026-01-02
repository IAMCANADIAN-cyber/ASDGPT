import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json
import requests

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.lmm_interface import LMMInterface
import config

class MockDataLogger:
    def __init__(self):
        self.logs = []
    def log_info(self, msg): self.logs.append(f"INFO: {msg}")
    def log_warning(self, msg): self.logs.append(f"WARN: {msg}")
    def log_error(self, msg, details=""): self.logs.append(f"ERROR: {msg} | {details}")
    def log_debug(self, msg): self.logs.append(f"DEBUG: {msg}")

class TestLMMRobustness(unittest.TestCase):
    def setUp(self):
        self.logger = MockDataLogger()
        self.lmm = LMMInterface(data_logger=self.logger)
        # Reduce retry/timeout settings for faster testing
        # We can't easily change the hardcoded retries in the method without editing code,
        # but we can mock the behavior.

    @patch('requests.post')
    def test_successful_response(self, mock_post):
        """Test a standard valid response."""
        expected_state = {"arousal": 50, "overload": 10, "focus": 80, "energy": 70, "mood": 60}
        response_content = {
            "state_estimation": expected_state,
            "suggestion": None
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(response_content)}}]
        }
        mock_post.return_value = mock_response

        result = self.lmm.process_data(user_context={"sensor_metrics": {}})
        self.assertIsNotNone(result)
        self.assertEqual(result["state_estimation"], expected_state)

    @patch('requests.post')
    def test_timeout_and_failure(self, mock_post):
        """Test complete failure (timeouts) returns Fallback state."""
        mock_post.side_effect = requests.exceptions.Timeout("Mock Timeout")

        result = self.lmm.process_data(user_context={"sensor_metrics": {}})

        # Should now return fallback state
        self.assertIsNotNone(result)
        self.assertTrue(result.get("is_fallback"))
        self.assertEqual(result["state_estimation"]["arousal"], 50)

        # Verify retries occurred
        self.assertEqual(mock_post.call_count, 3)

    @patch('requests.post')
    def test_internal_server_error(self, mock_post):
        """Test 500 errors returns Fallback state."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Error")
        mock_post.return_value = mock_response

        result = self.lmm.process_data(user_context={"sensor_metrics": {}})

        # Should now return fallback state
        self.assertIsNotNone(result)
        self.assertTrue(result.get("is_fallback"))
        self.assertEqual(mock_post.call_count, 3)

    @patch('requests.post')
    def test_malformed_json_response(self, mock_post):
        """Test valid HTTP response but invalid JSON content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is not JSON"}}]
        }
        mock_post.return_value = mock_response

        result = self.lmm.process_data(user_context={"sensor_metrics": {}})
        self.assertIsNotNone(result)
        self.assertTrue(result.get("is_fallback"))

    @patch('requests.post')
    def test_invalid_schema_missing_keys(self, mock_post):
        """Test JSON is valid but missing required keys."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"state_estimation": {"arousal": 50}})}}]
        }
        mock_post.return_value = mock_response

        result = self.lmm.process_data(user_context={"sensor_metrics": {}})
        self.assertIsNotNone(result)
        self.assertTrue(result.get("is_fallback"))

    @patch('requests.post')
    def test_invalid_schema_out_of_bounds(self, mock_post):
        """Test JSON is valid but values are out of bounds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        state = {"arousal": 150, "overload": 10, "focus": 80, "energy": 70, "mood": 60}
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"state_estimation": state, "suggestion": None})}}]
        }
        mock_post.return_value = mock_response

        result = self.lmm.process_data(user_context={"sensor_metrics": {}})
        self.assertIsNotNone(result)
        self.assertTrue(result.get("is_fallback"))

if __name__ == '__main__':
    unittest.main()
