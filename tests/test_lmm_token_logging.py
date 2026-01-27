import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.lmm_interface import LMMInterface
import config

class TestLMMTokenLogging(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.lmm_interface = LMMInterface(data_logger=self.mock_logger)
        # Ensure fallback is off so we don't accidentally test that
        config.LMM_FALLBACK_ENABLED = False

    @patch('requests.post')
    def test_token_usage_capture(self, mock_post):
        """
        Verify that token usage statistics are extracted from the LMM response,
        logged, and injected into the response metadata.
        """
        # Mock Response Content
        response_content = {
            "state_estimation": {
                "arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50
            },
            "suggestion": None
        }

        # Mock Usage Stats
        usage_stats = {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120
        }

        # Construct full response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(response_content)}}],
            "usage": usage_stats
        }
        mock_post.return_value = mock_response

        # Call process_data
        result = self.lmm_interface.process_data(user_context={"sensor_metrics": {}})

        # Assertions
        self.assertIsNotNone(result, "Result should not be None")

        # 1. Check Metadata Injection
        self.assertIn("_meta", result, "_meta should be present")
        self.assertIn("usage", result["_meta"], "usage should be in _meta")
        self.assertEqual(result["_meta"]["usage"], usage_stats, "Usage stats in _meta should match")

        # 2. Check Logging
        # Search for a log call containing the usage info
        log_calls = self.mock_logger.log_info.call_args_list
        found_log = False
        for call in log_calls:
            msg = call[0][0]
            if "Tokens: Prompt=100" in msg and "Completion=20" in msg:
                found_log = True
                break

        self.assertTrue(found_log, "Should have logged token usage")

    @patch('requests.post')
    def test_token_usage_missing(self, mock_post):
        """
        Verify that we handle missing usage stats gracefully.
        """
        response_content = {
            "state_estimation": {
                "arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50
            },
            "suggestion": None
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(response_content)}}]
            # No 'usage' key
        }
        mock_post.return_value = mock_response

        result = self.lmm_interface.process_data(user_context={"sensor_metrics": {}})

        self.assertIsNotNone(result)
        self.assertIn("usage", result["_meta"])
        self.assertEqual(result["_meta"]["usage"], {}, "Usage should be empty dict if missing")

if __name__ == '__main__':
    unittest.main()
