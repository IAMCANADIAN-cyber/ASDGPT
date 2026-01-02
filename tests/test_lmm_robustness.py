import unittest
from unittest.mock import MagicMock, patch
import time
import requests
import config
import numpy as np
from core.lmm_interface import LMMInterface
from core.logic_engine import LogicEngine

class TestLMMRobustness(unittest.TestCase):

    def setUp(self):
        # Reset config to defaults for testing
        config.LMM_FALLBACK_ENABLED = True
        config.LMM_CIRCUIT_BREAKER_MAX_FAILURES = 3 # Lower for testing
        config.LMM_CIRCUIT_BREAKER_COOLDOWN = 1 # Short for testing

        self.mock_logger = MagicMock()
        self.lmm_interface = LMMInterface(data_logger=self.mock_logger)
        self.logic_engine = LogicEngine(logger=self.mock_logger, lmm_interface=self.lmm_interface)

        # Override logic engine params for faster testing
        self.logic_engine.lmm_call_interval = 0.1
        self.logic_engine.min_lmm_interval = 0

        # Inject dummy data so LogicEngine triggers work
        self.logic_engine.last_video_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        self.logic_engine.last_audio_chunk = np.zeros(10)

    @patch('requests.post')
    def test_fallback_enabled(self, mock_post):
        """Test that LMMInterface returns fallback response when network fails."""
        # Simulate network failure
        mock_post.side_effect = requests.exceptions.ConnectionError("Network Error")

        response = self.lmm_interface.process_data(user_context={"sensor_metrics": {}})

        self.assertIsNotNone(response)
        self.assertTrue(response.get("_meta", {}).get("is_fallback"))
        self.assertEqual(response["state_estimation"]["arousal"], 50) # Neutral state

    @patch('requests.post')
    def test_fallback_disabled(self, mock_post):
        """Test that LMMInterface returns None when network fails and fallback disabled."""
        config.LMM_FALLBACK_ENABLED = False
        mock_post.side_effect = requests.exceptions.ConnectionError("Network Error")

        response = self.lmm_interface.process_data(user_context={"sensor_metrics": {}})

        self.assertIsNone(response)

        # Restore config
        config.LMM_FALLBACK_ENABLED = True

    def test_circuit_breaker_activates(self):
        """Test that LogicEngine stops calling LMM after consecutive failures."""

        # Mock LMM interface to always return fallback (which counts as failure for circuit breaker)

        fallback_response = {
            "state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50},
            "suggestion": None,
            "_meta": {"is_fallback": True}
        }

        # We mock process_data on the *instance* held by logic_engine
        self.logic_engine.lmm_interface.process_data = MagicMock(return_value=fallback_response)

        # Manually trigger multiple times
        # We need to wait for the thread to finish each time since LogicEngine spawns threads

        for i in range(config.LMM_CIRCUIT_BREAKER_MAX_FAILURES + 1):
             # Force trigger
             self.logic_engine._trigger_lmm_analysis(reason=f"test_{i}")
             # Wait for thread to finish
             if self.logic_engine.lmm_thread:
                 self.logic_engine.lmm_thread.join()

        # Check if circuit breaker is open
        # The cooldown should be active
        self.assertTrue(self.logic_engine.lmm_circuit_breaker_open_until > time.time())

        # Try to trigger again - should be skipped
        # Reset mock to ensure we don't count previous calls
        self.logic_engine.lmm_interface.process_data.reset_mock()

        self.logic_engine._trigger_lmm_analysis(reason="should_skip")

        # Verify process_data was NOT called
        self.logic_engine.lmm_interface.process_data.assert_not_called()

        # We expect a debug log saying "Skipping... Circuit breaker is OPEN"
        found_skip_msg = False
        for call in self.mock_logger.log_debug.call_args_list:
            if "Circuit breaker is OPEN" in str(call):
                found_skip_msg = True
                break

        self.assertTrue(found_skip_msg, "Did not find expected log message about circuit breaker skipping.")

    def test_circuit_breaker_resets(self):
        """Test that circuit breaker resets after cooldown."""

        # 1. Trip the breaker manually
        self.logic_engine.lmm_circuit_breaker_open_until = time.time() + 0.5 # Open for 0.5s
        self.logic_engine.lmm_consecutive_failures = config.LMM_CIRCUIT_BREAKER_MAX_FAILURES

        # 2. Wait
        time.sleep(0.6)

        # 3. Trigger again - should work (we'll mock success this time)
        success_response = {
            "state_estimation": {"arousal": 60, "overload": 10, "focus": 60, "energy": 60, "mood": 60},
            "suggestion": None
        }
        self.logic_engine.lmm_interface.process_data = MagicMock(return_value=success_response)

        self.logic_engine._trigger_lmm_analysis(reason="recovery_test")
        if self.logic_engine.lmm_thread:
                 self.logic_engine.lmm_thread.join()

        self.assertEqual(self.logic_engine.lmm_consecutive_failures, 0)

if __name__ == '__main__':
    unittest.main()
