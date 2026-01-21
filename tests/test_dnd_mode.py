import unittest
from unittest.mock import MagicMock, patch
import time
import numpy as np
from core.logic_engine import LogicEngine
import config

class TestDNDMode(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_lmm = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_intervention_engine = MagicMock()

        self.engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm
        )
        self.engine.set_intervention_engine(self.mock_intervention_engine)

        # Configure thresholds for easy triggering
        self.engine.audio_threshold_high = 0.5
        self.engine.video_activity_threshold_high = 10.0
        self.engine.lmm_call_interval = 100  # Long interval to avoid periodic triggers interfering
        self.engine.min_lmm_interval = 0

    @patch('threading.Thread')
    def test_active_triggers_high_audio(self, mock_thread):
        """Verify Active mode triggers LMM on high audio."""
        self.engine.set_mode("active")

        # Simulate High Audio
        self.engine.audio_level = 0.8
        self.engine.audio_analysis = {"is_speech": True}

        mock_payload = {
            'user_context': {
                'sensor_metrics': {'audio_level': 0.8}
            },
            'data': 'mock'
        }
        with patch.object(self.engine, '_prepare_lmm_data', return_value=mock_payload):
            self.engine.update()

        # Verify thread started with allow_intervention=True
        mock_thread.assert_called()
        args, kwargs = mock_thread.call_args
        target = kwargs.get('target')
        call_args = kwargs.get('args') # (lmm_payload, allow_intervention)

        self.assertEqual(target, self.engine._run_lmm_analysis_async)
        self.assertTrue(call_args[1]) # allow_intervention should be True

    @patch('threading.Thread')
    def test_dnd_monitors_high_audio(self, mock_thread):
        """Verify IMPROVED behavior: DND mode monitors high audio triggers but suppresses intervention."""
        self.engine.set_mode("dnd")

        # Simulate High Audio
        self.engine.audio_level = 0.8
        self.engine.audio_analysis = {"is_speech": True}

        # Reset lmm timer to avoid periodic trigger
        self.engine.last_lmm_call_time = time.time()

        mock_payload = {
            'user_context': {
                'sensor_metrics': {'audio_level': 0.8}
            },
            'data': 'mock'
        }
        with patch.object(self.engine, '_prepare_lmm_data', return_value=mock_payload):
            self.engine.update()

        # Verify thread STARTED (to monitor state)
        mock_thread.assert_called()
        args, kwargs = mock_thread.call_args
        call_args = kwargs.get('args')

        # BUT intervention should be suppressed
        self.assertFalse(call_args[1]) # allow_intervention should be False

    @patch('threading.Thread')
    def test_dnd_periodic_suppression(self, mock_thread):
        """Verify DND mode suppresses intervention on periodic check."""
        self.engine.set_mode("dnd")

        # Force periodic check
        self.engine.last_lmm_call_time = time.time() - 200

        mock_payload = {
            'user_context': {
                'sensor_metrics': {'audio_level': 0.8}
            },
            'data': 'mock'
        }
        with patch.object(self.engine, '_prepare_lmm_data', return_value=mock_payload):
            self.engine.update()

        # Verify thread started with allow_intervention=False
        mock_thread.assert_called()
        args, kwargs = mock_thread.call_args
        call_args = kwargs.get('args')
        self.assertFalse(call_args[1]) # allow_intervention should be False

if __name__ == '__main__':
    unittest.main()
