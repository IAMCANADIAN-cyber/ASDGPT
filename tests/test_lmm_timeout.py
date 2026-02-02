import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time
import requests
import threading

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface
import config

class SynchronousThread:
    """Helper to run threads synchronously for testing."""
    def __init__(self, target, args=(), daemon=False):
        self.target = target
        self.args = args
        self.daemon = daemon

    def start(self):
        self.target(*self.args)

    def is_alive(self):
        return False

    def join(self, timeout=None):
        pass

class TestLMMTimeout(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_intervention = MagicMock()

        # Patch config to ensure fallback is enabled and thresholds are low for testing
        self.config_patcher = patch.multiple(config,
            LMM_FALLBACK_ENABLED=True,
            LMM_CIRCUIT_BREAKER_MAX_FAILURES=2,
            LMM_CIRCUIT_BREAKER_COOLDOWN=100
        )
        self.config_patcher.start()

        # Initialize LMM Interface
        self.lmm_interface = LMMInterface(data_logger=self.mock_logger)
        # We need to ensure the interface picks up the patched config values if it reads them in __init__
        # LMMInterface reads config in __init__, so we are good as we patched before init.
        # However, it also has `self.circuit_max_failures = getattr(config, ...)` which is good.

        # Initialize LogicEngine
        self.engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger,
            lmm_interface=self.lmm_interface
        )
        self.engine.set_intervention_engine(self.mock_intervention)

        # Configure Engine Thresholds
        self.engine.audio_threshold_high = 0.5
        self.engine.lmm_call_interval = 5
        self.engine.min_lmm_interval = 1
        self.engine.max_error_recovery_attempts = 3

        # Sync Thread Patch
        self.thread_patcher = patch('threading.Thread', side_effect=SynchronousThread)
        self.thread_patcher.start()

        # Time Sleep Patch (to speed up retries)
        self.sleep_patcher = patch('time.sleep')
        self.sleep_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()
        self.thread_patcher.stop()
        self.sleep_patcher.stop()

    def test_timeout_trips_circuit_breaker_and_triggers_fallback(self):
        """
        Verifies that repeated LMM timeouts:
        1. Increment failure counters.
        2. Trip the circuit breaker.
        3. Trigger offline fallback logic in LogicEngine.
        """

        # Setup sensor data to trigger analysis
        self.engine.audio_level = 0.8
        self.engine.audio_analysis = {"is_speech": True}
        # Ensure we have video data so _prepare_lmm_data doesn't return None
        self.engine.last_video_frame = MagicMock()
        # (Actually LogicEngine checks `last_video_frame is None and last_audio_chunk is None`)
        # We need to set them.
        import numpy as np
        self.engine.last_audio_chunk = np.zeros(1024)

        # Mock requests.post to timeout
        with patch('requests.post', side_effect=requests.exceptions.Timeout("Connection timed out")):

            # --- Cycle 1: Timeout ---
            # Manually trigger LMM analysis via update or direct method
            # We'll use update() to test the full loop, but we need to control time.

            current_time = 1000.0
            self.engine.last_lmm_call_time = current_time - 10 # Allow trigger

            with patch('time.time', return_value=current_time):
                self.engine.update()

            # Verification 1:
            # - requests.post called (retried 3 times internally by LMMInterface)
            # - LogicEngine should have incremented failure count?
            # LMMInterface catches Timeout, increments its circuit_failures.
            # It returns None (since fallback enabled but circuit not open yet? Or returns fallback?)
            # LMMInterface logic:
            # if failures >= max: open circuit.
            # if request fails: failures++. check max. return None (or fallback if max reached during this call? No)
            # LogicEngine receives None. Increments self.lmm_consecutive_failures.

            # Let's check logic_engine state
            # LogicEngine.lmm_consecutive_failures should be 1
            # LMMInterface.circuit_failures should be 1 (after 3 retries)
            # Note: LMMInterface increments failure count *once* per process_data call if all retries fail.

            self.assertGreater(self.engine.lmm_consecutive_failures, 0, "LogicEngine should track failure")
            self.assertGreater(self.lmm_interface.circuit_failures, 0, "LMMInterface should track failure")

            # --- Cycle 2: Timeout (Trip Breaker) ---
            # We set MAX_FAILURES = 2. So this second failure should trip it.

            current_time += 10 # Advance time
            self.engine.last_lmm_call_time = current_time - 10

            with patch('time.time', return_value=current_time):
                self.engine.update()

            # Verification 2:
            # LogicEngine failures should be 2.
            # LMMInterface failures should be 2.
            # LogicEngine should log Circuit Breaker OPENED.

            self.assertGreaterEqual(self.engine.lmm_consecutive_failures, 2)
            self.assertTrue(self.engine.lmm_circuit_breaker_open_until > current_time, "LogicEngine Circuit Breaker should be open")

            # --- Cycle 3: Fallback Trigger ---
            # Now breaker is open. Next update should skip LMM and run offline fallback.

            current_time += 10
            self.engine.last_lmm_call_time = current_time - 10 # This controls "periodic" or event check
            # But wait, LogicEngine logic:
            # if trigger_lmm:
            #    if circuit_open:
            #       _run_offline_fallback_logic()

            # We need to ensure trigger_lmm is True.
            # High audio level + speech = trigger_lmm = True.

            # Reset mock intervention to verify new call
            self.mock_intervention.start_intervention.reset_mock()

            with patch('time.time', return_value=current_time):
                self.engine.update()

            # Verification 3:
            # Intervention should be called with offline_noise_reduction
            self.mock_intervention.start_intervention.assert_called_once()
            call_args = self.mock_intervention.start_intervention.call_args[0][0]
            self.assertEqual(call_args.get("type"), "offline_noise_reduction")
            self.assertIn("offline", call_args.get("message", "").lower())

if __name__ == '__main__':
    unittest.main()
