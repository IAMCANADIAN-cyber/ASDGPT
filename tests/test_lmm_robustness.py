import unittest
from unittest.mock import MagicMock, patch
import time
import sys
import os
import requests

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.lmm_interface import LMMInterface
import config

class TestLMMRobustness(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.lmm = LMMInterface(data_logger=self.mock_logger)

        # Override config for faster testing
        self.lmm.circuit_max_failures = 3
        self.lmm.circuit_cooldown = 1 # 1 second cooldown
        config.LMM_FALLBACK_ENABLED = True

    def test_fallback_response(self):
        """Test that fallback response is returned when LMM fails."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException("Connection Refused")

            # Should fail 3 times (retries) then return fallback
            response = self.lmm.process_data(user_context={"sensor_metrics": {}})

            self.assertIsNotNone(response)
            self.assertIsNone(response.get("suggestion"))
            self.assertEqual(response["state_estimation"]["arousal"], 50)
            self.assertEqual(mock_post.call_count, 3)

    def test_circuit_breaker_activates(self):
        """Test that circuit breaker trips after max failures."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException("Connection Refused")

            # 1st call (fails 3 times due to retries inside process_data)
            # wait, process_data retries 3 times internally.
            # Does circuit breaker count individual call failures or internal retries?
            # Implementation:
            # except RequestException: ... loop ...
            # After loop: self.circuit_failures += 1
            # So one process_data call = 1 failure count (even if it retried 3 times internally).

            self.lmm.process_data(user_context={"sensor_metrics": {}})
            self.assertEqual(self.lmm.circuit_failures, 1)

            # 2nd call
            self.lmm.process_data(user_context={"sensor_metrics": {}})
            self.assertEqual(self.lmm.circuit_failures, 2)

            # 3rd call - Should trip breaker
            self.lmm.process_data(user_context={"sensor_metrics": {}})
            self.assertEqual(self.lmm.circuit_failures, 3)
            self.assertGreater(self.lmm.circuit_open_time, 0)

            # 4th call - Should NOT call requests, but return fallback
            mock_post.reset_mock()
            response = self.lmm.process_data(user_context={"sensor_metrics": {}})

            mock_post.assert_not_called() # Circuit is open!
            self.assertIsNotNone(response) # Fallback still works

            # Wait for cooldown
            time.sleep(1.1)

            # 5th call - Should retry
            self.lmm.process_data(user_context={"sensor_metrics": {}})
            mock_post.assert_called()

if __name__ == '__main__':
    unittest.main()
