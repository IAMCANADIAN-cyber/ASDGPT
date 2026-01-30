import unittest
import time
import sys
import os
import threading
import numpy as np
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.logic_engine import LogicEngine
from core.data_logger import DataLogger
import config

class MockLMMInterface:
    def __init__(self):
        self.call_count = 0
        self.should_fail = False
        self.should_return_fallback = False

    def process_data(self, video_data=None, audio_data=None, user_context=None):
        self.call_count += 1
        if self.should_fail:
            # Simulate hard failure (return None or raise exception depending on impl, LogicEngine handles None)
            return None

        if self.should_return_fallback:
            return {
                "state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50},
                "visual_context": [],
                "suggestion": None,
                "_meta": {"is_fallback": True}
            }

        return {
            "state_estimation": {"arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50},
            "visual_context": [],
            "suggestion": {"type": "test_intervention", "message": "Test"}
        }

    def get_intervention_suggestion(self, analysis):
        return analysis.get("suggestion")

class TestLMMCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.logger = DataLogger(log_file_path="test_circuit_breaker.log")
        self.mock_lmm = MockLMMInterface()
        self.logic_engine = LogicEngine(logger=self.logger, lmm_interface=self.mock_lmm)

        # Configure thresholds
        self.logic_engine.lmm_call_interval = 0.1 # Fast for test
        self.logic_engine.min_lmm_interval = 0

        # Inject mock data so _prepare_lmm_data succeeds
        self.logic_engine.last_video_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.logic_engine.last_audio_chunk = np.zeros(1024)

    def tearDown(self):
        self.logic_engine.shutdown()

    @patch('config.LMM_CIRCUIT_BREAKER_MAX_FAILURES', 3)
    @patch('config.LMM_CIRCUIT_BREAKER_COOLDOWN', 2)
    def test_circuit_breaker_logic(self):
        """
        Test that circuit breaker opens after MAX_FAILURES and prevents calls during COOLDOWN.
        """
        # 1. Simulate Failures
        self.mock_lmm.should_fail = True

        # Trigger 1 (Fail)
        self.logic_engine._trigger_lmm_analysis(reason="test")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()
        self.assertEqual(self.logic_engine.lmm_consecutive_failures, 1)

        # Trigger 2 (Fail)
        self.logic_engine._trigger_lmm_analysis(reason="test")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()
        self.assertEqual(self.logic_engine.lmm_consecutive_failures, 2)

        # Trigger 3 (Fail) -> Should OPEN breaker
        self.logic_engine._trigger_lmm_analysis(reason="test")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()
        self.assertEqual(self.logic_engine.lmm_consecutive_failures, 3)
        self.assertGreater(self.logic_engine.lmm_circuit_breaker_open_until, time.time())

        # 2. Verify Breaker is Open
        initial_call_count = self.mock_lmm.call_count
        self.logic_engine._trigger_lmm_analysis(reason="test_blocked")

        # Thread should NOT start
        if self.logic_engine.lmm_thread and self.logic_engine.lmm_thread.is_alive():
             self.logic_engine.lmm_thread.join()

        # Call count should NOT have increased
        self.assertEqual(self.mock_lmm.call_count, initial_call_count, "LMM call should be skipped when breaker is open")

        # 3. Wait for Cooldown
        time.sleep(2.1) # Wait > COOLDOWN (2s)

        # 4. Verify Breaker Resets on Success
        self.mock_lmm.should_fail = False
        self.logic_engine._trigger_lmm_analysis(reason="test_recovery")
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        self.assertEqual(self.logic_engine.lmm_consecutive_failures, 0, "Failures should reset on success")
        self.assertEqual(self.mock_lmm.call_count, initial_call_count + 1)

if __name__ == '__main__':
    unittest.main()
