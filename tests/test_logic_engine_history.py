import unittest
from unittest.mock import MagicMock, patch
import time
import collections
from core.logic_engine import LogicEngine
import config

class TestLogicEngineHistory(unittest.TestCase):
    def setUp(self):
        self.mock_window_sensor = MagicMock()
        self.mock_window_sensor.get_active_window.return_value = "Test Window"

        # Patch config to lower interval for testing
        self.patcher = patch('core.logic_engine.config.HISTORY_SAMPLE_INTERVAL', 1, create=True)
        self.mock_interval = self.patcher.start()

        self.logic_engine = LogicEngine(window_sensor=self.mock_window_sensor)
        # Manually set interval in instance if it was already initialized with default (it was)
        self.logic_engine.history_sample_interval = 0.1 # Very fast for test

    def tearDown(self):
        self.patcher.stop()

    def test_history_initialization(self):
        self.assertIsInstance(self.logic_engine.context_history, collections.deque)
        self.assertEqual(len(self.logic_engine.context_history), 0)
        self.assertEqual(self.logic_engine.context_history.maxlen, 10)

    def test_history_accumulation(self):
        # Simulate time passing and update
        start_time = time.time()

        # First update - should add entry
        self.logic_engine.last_history_sample_time = start_time - 1.0 # Force update
        self.logic_engine.update()

        self.assertEqual(len(self.logic_engine.context_history), 1)
        entry = self.logic_engine.context_history[0]
        self.assertEqual(entry['active_window'], "Test Window")
        self.assertEqual(entry['mode'], config.DEFAULT_MODE)
        self.assertAlmostEqual(entry['timestamp'], time.time(), delta=1.0)

    def test_history_rotation(self):
        # Fill history
        self.logic_engine.history_sample_interval = 0 # Updates every call

        for i in range(15):
            self.mock_window_sensor.get_active_window.return_value = f"Window {i}"
            # We need to manually advance last_history_sample_time or force logic to trigger
            # LogicEngine sets last_sample_time = current_time.
            # So we rely on time.time() changing or force interval to 0.
            # But computer is fast, time.time() might be same.
            # Let's mock time.
            with patch('time.time', return_value=1000 + i):
                 self.logic_engine.update()

        self.assertEqual(len(self.logic_engine.context_history), 10)
        # Should have discarded 0-4, keeping 5-14
        self.assertEqual(self.logic_engine.context_history[0]['active_window'], "Window 5")
        self.assertEqual(self.logic_engine.context_history[-1]['active_window'], "Window 14")

    def test_prepare_lmm_data_includes_history(self):
        # Add some history
        self.logic_engine.context_history.append({
            "timestamp": 1234567890,
            "mode": "active",
            "active_window": "Old Window"
        })

        # Prepare data requires some sensor data or mocks to return not None
        self.logic_engine.last_video_frame = MagicMock() # Just not None

        data = self.logic_engine._prepare_lmm_data()
        self.assertIsNotNone(data)
        user_context = data['user_context']
        self.assertIn('history', user_context)
        self.assertEqual(len(user_context['history']), 1)
        self.assertEqual(user_context['history'][0]['active_window'], "Old Window")

if __name__ == '__main__':
    unittest.main()
