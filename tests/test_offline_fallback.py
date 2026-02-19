import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.logic_engine import LogicEngine

class TestOfflineFallback(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_lmm = MagicMock()
        self.mock_intervention = MagicMock()

        self.engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm
        )
        self.engine.set_intervention_engine(self.mock_intervention)

        # Config defaults relevant to tests
        self.engine.audio_threshold_high = 0.5
        self.engine.video_activity_threshold_high = 0.5
        self.engine.lmm_call_interval = 5
        self.engine.min_lmm_interval = 2

    def test_offline_fallback_triggers_noise_intervention(self):
        """Test that high noise triggers offline intervention when LMM circuit breaker is open."""

        # 1. Simulate Circuit Breaker Open
        self.engine.lmm_circuit_breaker_open_until = time.time() + 100

        # 2. Simulate High Audio Noise & Speech
        self.engine.audio_level = 0.8  # > 0.5
        self.engine.audio_analysis = {"is_speech": True}

        # 3. Last call time allows trigger
        self.engine.last_lmm_call_time = time.time() - 10

        # 4. Mock start_intervention
        self.mock_intervention.start_intervention = MagicMock()

        # 5. Call Update
        with patch('time.time', return_value=self.engine.last_lmm_call_time + 10):
            self.engine.update()

        # 6. Verify LMM was NOT triggered (skipped due to breaker)
        # Note: logic_engine._trigger_lmm_analysis would return early, but we want verify
        # that we diverted to fallback.
        # Check logs for "Circuit breaker is OPEN" or "Offline Fallback"

        # 7. Verify Intervention Triggered
        self.mock_intervention.start_intervention.assert_called()
        call_args = self.mock_intervention.start_intervention.call_args[0][0]
        self.assertEqual(call_args.get("type"), "offline_noise_reduction")
        self.assertIn("offline", call_args.get("message", "").lower())

    def test_offline_fallback_delegation(self):
        """Test that offline fallback delegates to InterventionEngine."""
        self.engine.lmm_circuit_breaker_open_until = time.time() + 100
        self.engine.audio_level = 0.8
        self.engine.audio_analysis = {"is_speech": True}
        self.engine.last_lmm_call_time = time.time() - 10

        self.mock_intervention.start_intervention = MagicMock()

        with patch('time.time', return_value=self.engine.last_lmm_call_time + 10):
             self.engine.update()

        # Should call start_intervention
        self.mock_intervention.start_intervention.assert_called()

        # Verify category
        call_args = self.mock_intervention.start_intervention.call_args
        # call_args is a tuple (args, kwargs) or just args if accessed differently.
        # MagicMock.call_args returns (args, kwargs)
        args, kwargs = call_args
        self.assertEqual(kwargs.get("category"), "offline_fallback")

    def test_offline_fallback_video_trigger(self):
        """Test high video activity triggers fallback."""
        self.engine.lmm_circuit_breaker_open_until = time.time() + 100
        self.engine.video_activity = 0.8
        self.engine.face_metrics = {"face_detected": True}
        self.engine.last_lmm_call_time = time.time() - 10

        self.mock_intervention.start_intervention = MagicMock()

        with patch('time.time', return_value=self.engine.last_lmm_call_time + 10):
            self.engine.update()

        self.mock_intervention.start_intervention.assert_called()
        call_args = self.mock_intervention.start_intervention.call_args[0][0]
        self.assertEqual(call_args.get("type"), "offline_activity_reduction")

if __name__ == '__main__':
    unittest.main()
