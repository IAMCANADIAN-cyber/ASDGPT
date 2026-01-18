import sys
import os
import unittest
import time
import json
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.lmm_interface import LMMInterface
import config

class TestLMMLatency(unittest.TestCase):
    def setUp(self):
        # Mock logger
        self.mock_logger = MagicMock()
        self.lmm_interface = LMMInterface(data_logger=self.mock_logger)

    @patch('requests.post')
    def test_latency_monitoring(self, mock_post):
        """
        Test that LMM latency is calculated, logged, and returned in _meta.
        """
        print("\n--- Test: LMM Latency Monitoring ---")

        # Define a mock response content
        response_content = {
            "state_estimation": {"arousal": 50, "overload": 20, "focus": 80, "energy": 60, "mood": 50},
            "visual_context": ["latency_test"],
            "suggestion": None
        }

        # Setup mock behavior with a delay
        def mock_post_side_effect(*args, **kwargs):
            time.sleep(0.1) # Sleep for 100ms
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": f"```json\n{json.dumps(response_content)}\n```"
                    }
                }]
            }
            return mock_response

        mock_post.side_effect = mock_post_side_effect

        # Call process_data
        user_context = {"sensor_metrics": {"audio_level": 0.0}}
        result = self.lmm_interface.process_data(user_context=user_context)

        # Assertions
        self.assertIsNotNone(result, "Result should not be None")
        self.assertIn("_meta", result, "Result should contain '_meta' key")
        self.assertIn("latency_ms", result["_meta"], "_meta should contain 'latency_ms'")

        latency = result["_meta"]["latency_ms"]
        print(f"Measured Latency: {latency:.2f}ms")

        # Expect at least 100ms (from sleep)
        self.assertGreaterEqual(latency, 100.0, "Latency should be at least 100ms")
        # Allow some overhead, but shouldn't be excessive (e.g. > 500ms for a 100ms sleep)
        self.assertLess(latency, 1000.0, "Latency calculation seems too high")

        # Verify logging
        # Check if any log_info call contains "Latency"
        log_calls = [args[0] for args, _ in self.mock_logger.log_info.call_args_list]
        latency_log_exists = any("Latency:" in call for call in log_calls)
        self.assertTrue(latency_log_exists, "Should log latency info")

if __name__ == '__main__':
    unittest.main()
