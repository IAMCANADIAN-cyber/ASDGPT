import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from collections import deque
import config
from core.logic_engine import LogicEngine

class TestRapidSwitching(unittest.TestCase):
    def setUp(self):
        self.logic_engine = LogicEngine()
        # Mock window sensor
        self.logic_engine.window_sensor = MagicMock()
        self.logic_engine.window_sensor.get_active_window.return_value = "Test App"

        # Ensure _prepare_lmm_data doesn't return None
        self.logic_engine.last_audio_chunk = np.zeros(1024)

    def test_rapid_switching_alert(self):
        """Verify alert is generated when unique windows >= threshold."""
        # Populate history with 4 unique windows
        history_data = [
            {'timestamp': 100, 'active_window': 'App A', 'mode': 'active'},
            {'timestamp': 101, 'active_window': 'App B', 'mode': 'active'},
            {'timestamp': 102, 'active_window': 'App C', 'mode': 'active'},
            {'timestamp': 103, 'active_window': 'App D', 'mode': 'active'},
            {'timestamp': 104, 'active_window': 'App A', 'mode': 'active'},
        ]

        self.logic_engine.context_history = deque(history_data, maxlen=5)

        # Patch config to ensure threshold is 4
        with patch.object(config, 'RAPID_SWITCHING_THRESHOLD', 4, create=True):
             lmm_data = self.logic_engine._prepare_lmm_data(trigger_reason="test")

        self.assertIsNotNone(lmm_data, "LMM Data should not be None")
        user_context = lmm_data['user_context']
        system_alerts = user_context.get('system_alerts', [])

        self.assertIn("Rapid Task Switching Detected", system_alerts)

    def test_stable_window_no_alert(self):
        """Verify no alert when windows are stable."""
        history_data = [
            {'timestamp': 100, 'active_window': 'App A', 'mode': 'active'},
            {'timestamp': 101, 'active_window': 'App A', 'mode': 'active'},
            {'timestamp': 102, 'active_window': 'App A', 'mode': 'active'},
            {'timestamp': 103, 'active_window': 'App B', 'mode': 'active'}, # Just 2 unique
            {'timestamp': 104, 'active_window': 'App A', 'mode': 'active'},
        ]

        self.logic_engine.context_history = deque(history_data, maxlen=5)

        with patch.object(config, 'RAPID_SWITCHING_THRESHOLD', 4, create=True):
             lmm_data = self.logic_engine._prepare_lmm_data(trigger_reason="test")

        user_context = lmm_data['user_context']
        system_alerts = user_context.get('system_alerts', [])

        self.assertNotIn("Rapid Task Switching Detected", system_alerts)

if __name__ == '__main__':
    unittest.main()
