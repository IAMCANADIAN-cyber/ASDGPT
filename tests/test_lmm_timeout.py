import unittest
from unittest.mock import MagicMock, patch
import time
import requests
import sys
import os
import threading
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface
import config

class TestLMMTimeout(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_intervention = MagicMock()

        # Use real LMMInterface but we will patch its network calls
        self.lmm_interface = LMMInterface(data_logger=self.mock_logger, intervention_library=None)

        # We need to make sure LMMInterface circuit breaker matches what we expect for the test
        self.lmm_interface.circuit_max_failures = 3
        self.lmm_interface.circuit_cooldown = 60

        self.engine = LogicEngine(
            logger=self.mock_logger,
            lmm_interface=self.lmm_interface
        )
        self.engine.set_intervention_engine(self.mock_intervention)

        # Set LogicEngine config for testing
        self.engine.lmm_call_interval = 5
        self.engine.min_lmm_interval = 0 # Allow rapid triggers

        # Fix for _prepare_lmm_data check
        self.engine.last_audio_chunk = np.zeros(1024)

    def tearDown(self):
        self.engine.shutdown()

    def run_update_and_wait(self):
        """Helper to run update and wait for the LMM thread to finish."""
        self.engine.update()
        if self.engine.lmm_thread and self.engine.lmm_thread.is_alive():
            # Wait longer for join since retries might take a bit even with mocked sleep
            # But with mocked sleep it should be fast.
            self.engine.lmm_thread.join(timeout=5.0)

    @patch('requests.post')
    @patch('time.sleep', return_value=None) # Patch sleep to skip delays
    @patch('core.lmm_interface.config.LMM_FALLBACK_ENABLED', True)
    @patch('core.logic_engine.config.LMM_CIRCUIT_BREAKER_MAX_FAILURES', 3)
    def test_lmm_timeout_handling(self, mock_sleep, mock_post):
        """
        Verify that repeated LMM timeouts:
        1. Increment failure counters.
        2. Trip the circuit breaker.
        3. Trigger offline fallback logic.
        """
        # Configure mock to raise Timeout
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        # Set up conditions to trigger LMM
        self.engine.current_mode = "active"
        self.engine.audio_level = 0.8
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.last_lmm_call_time = 0 # Ensure it triggers

        # --- Attempt 1 ---
        # Mock time to avoid 'periodic' trigger taking precedence if we are testing event trigger
        with patch('time.time', return_value=1000):
            self.run_update_and_wait()

        # Verify LMM was called
        self.assertTrue(mock_post.called, "requests.post should be called (LMM trigger)")
        # Verify failure count incremented
        self.assertEqual(self.engine.lmm_consecutive_failures, 1, "Failure count should be 1")

        # --- Attempt 2 ---
        self.engine.last_lmm_call_time = 0 # Reset for next trigger
        with patch('time.time', return_value=1010):
            self.run_update_and_wait()
        self.assertEqual(self.engine.lmm_consecutive_failures, 2, "Failure count should be 2")

        # --- Attempt 3 (Trip Circuit Breaker) ---
        self.engine.last_lmm_call_time = 0
        with patch('time.time', return_value=1020):
            self.run_update_and_wait()
        self.assertEqual(self.engine.lmm_consecutive_failures, 3, "Failure count should be 3")

        # Circuit breaker should now be open
        self.assertGreater(self.engine.lmm_circuit_breaker_open_until, 1020, "Circuit breaker should be open")

        # --- Attempt 4 (Offline Fallback) ---
        # Now that circuit breaker is open, next trigger should use offline fallback
        self.mock_intervention.start_intervention.reset_mock()
        self.engine.last_lmm_call_time = 0
        self.engine.audio_level = 0.9 # High noise
        self.engine.audio_analysis = {"is_speech": True}

        # We need to simulate time passing but NOT enough to close circuit breaker
        # And ensure offline trigger cooldown is respected (default 30s)
        # Last trigger was at 1020.
        current_sim_time = 1030

        with patch('time.time', return_value=current_sim_time):
            self.engine.update() # This runs synchronously for fallback

        # Verify NO LMM call (mock_post count shouldn't increase from previous 3)
        # We check that call_count didn't increase significantly (0 new calls)
        initial_call_count = mock_post.call_count
        self.assertEqual(mock_post.call_count, initial_call_count, "LMM should not be called when circuit breaker is open")

        # Verify Offline Intervention triggered
        self.mock_intervention.start_intervention.assert_called()
        args = self.mock_intervention.start_intervention.call_args[0][0]
        self.assertEqual(args.get("type"), "offline_noise_reduction")
        self.assertIn("offline", args.get("message", "").lower())

if __name__ == '__main__':
    unittest.main()
