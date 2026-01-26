import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.lmm_interface import LMMInterface

class TestLMMTokenLogging(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.lmm_interface = LMMInterface(data_logger=self.mock_logger)

        # Sample valid response content
        self.valid_response_content = json.dumps({
            "state_estimation": {
                "arousal": 50, "overload": 10, "focus": 80, "energy": 60, "mood": 70
            },
            "visual_context": ["working"],
            "suggestion": None
        })

    @patch('requests.post')
    def test_token_usage_logging_and_metadata(self, mock_post):
        """
        Verify that token usage is extracted, logged, and added to metadata.
        """
        # Mock Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": self.valid_response_content
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        mock_post.return_value = mock_response

        # Call process_data
        result = self.lmm_interface.process_data(video_data="fake_base64", user_context={})

        # 1. Verify result is valid
        self.assertIsNotNone(result)

        # 2. Verify _meta contains usage
        self.assertIn("_meta", result)
        self.assertIn("usage", result["_meta"])
        usage = result["_meta"]["usage"]
        self.assertEqual(usage["prompt_tokens"], 100)
        self.assertEqual(usage["completion_tokens"], 50)
        self.assertEqual(usage["total_tokens"], 150)

        # 3. Verify Logger was called with usage stats
        # We look for a log call that contains "Token Usage" or similar,
        # or specifically the numbers.
        # Since I haven't implemented the logging message yet, I will look for general info logs
        # and print them to see what I might expect, or just assert that *some* info log happened
        # which will eventually contain the string I define.
        # For now, I'll assert that I can find the values in one of the calls.

        found_usage_log = False
        for call in self.mock_logger.log_info.call_args_list:
            args, _ = call
            msg = args[0]
            if "Token Usage" in msg and "150" in msg:
                found_usage_log = True
                break

        self.assertTrue(found_usage_log, "Logger should have logged token usage stats.")

if __name__ == '__main__':
    unittest.main()
