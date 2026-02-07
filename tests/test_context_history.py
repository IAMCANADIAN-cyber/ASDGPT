import unittest
from unittest.mock import MagicMock, patch
import time
from collections import deque
import config
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface

class TestContextHistory(unittest.TestCase):
    def setUp(self):
        self.logic_engine = LogicEngine()
        # Mock window sensor
        self.logic_engine.window_sensor = MagicMock()
        self.logic_engine.window_sensor.get_active_window.return_value = "Test App"

        # Override config for faster testing
        self.orig_interval = config.HISTORY_SAMPLE_INTERVAL
        config.HISTORY_SAMPLE_INTERVAL = 0.1 # fast sample

    def tearDown(self):
        config.HISTORY_SAMPLE_INTERVAL = self.orig_interval

    def test_history_accumulation(self):
        """Verify history accumulates and respects maxlen."""
        # Force accumulation
        self.logic_engine.last_history_sample_time = 0
        self.logic_engine.update() # Should add 1

        self.assertEqual(len(self.logic_engine.context_history), 1)
        snapshot = self.logic_engine.context_history[0]
        self.assertEqual(snapshot['active_window'], "Test App")

        # Add more
        for i in range(10):
            time.sleep(0.11)
            self.logic_engine.window_sensor.get_active_window.return_value = f"App {i}"
            self.logic_engine.update()

        # Verify max len (default 5)
        self.assertEqual(len(self.logic_engine.context_history), config.HISTORY_WINDOW_SIZE)
        # Verify rolling: last one should be App 9
        self.assertEqual(self.logic_engine.context_history[-1]['active_window'], "App 9")

    def test_lmm_interface_formatting(self):
        """Verify LMM Interface formats the history correctly."""
        lmm = LMMInterface()

        # Construct a fake history with richer metrics
        now = time.time()
        history = [
            {
                'timestamp': now - 40,
                'active_window': 'Old App',
                'mode': 'active',
                'face_detected': True,
                'posture': 'neutral',
                'audio_level': 0.05,
                'video_activity': 2.5
            },
            {
                'timestamp': now - 10,
                'active_window': 'New App',
                'mode': 'active',
                'face_detected': False,
                'posture': 'slouching',
                'audio_level': 0.55,
                'video_activity': 15.2
            },
        ]

        user_context = {
            'context_history': history,
            'sensor_metrics': {}
        }

        # Mock requests to avoid network calls
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'choices': [{'message': {'content': '{"state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50}}'}}]
            }

            lmm.process_data(video_data=None, audio_data=None, user_context=user_context)

            # Inspect the prompt sent
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            messages = payload['messages']
            # content is a list of dicts or string. logic engine sends list of dicts.
            user_content = messages[1]['content']

            # Find the text part
            text_part = ""
            for part in user_content:
                if part['type'] == 'text':
                    text_part = part['text']
                    break

            # Debug output if needed
            # print(text_part)

            self.assertIn("Recent History (Last 5 snapshots):", text_part)
            self.assertIn("- T-40s: Window='Old App'", text_part)
            # Verify new fields are present
            self.assertIn("Posture=neutral", text_part)
            self.assertIn("Audio=0.05", text_part)
            self.assertIn("Motion=2.5", text_part)

            self.assertIn("- T-10s: Window='New App'", text_part)
            self.assertIn("Posture=slouching", text_part)
            self.assertIn("Audio=0.55", text_part)
            self.assertIn("Motion=15.2", text_part)

if __name__ == '__main__':
    unittest.main()
