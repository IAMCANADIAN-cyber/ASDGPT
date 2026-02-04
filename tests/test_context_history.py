import unittest
from unittest.mock import MagicMock, patch
import time
from collections import deque
import config
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface

class TestContextHistory(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_logger = MagicMock()
        self.mock_lmm_interface = MagicMock(spec=LMMInterface)
        self.mock_window_sensor = MagicMock()
        self.mock_window_sensor.get_active_window.return_value = "TestApp"

        # Patch config values for test control
        self.config_patcher = patch.multiple('config',
                                             HISTORY_SAMPLE_INTERVAL=1.0,
                                             HISTORY_WINDOW_SIZE=3)
        self.config_patcher.start()

        # Initialize LogicEngine
        self.logic_engine = LogicEngine(
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm_interface,
            window_sensor=self.mock_window_sensor
        )

        # Ensure deque is using the patched size (though constructor runs after patch, so should be fine)
        # But LogicEngine constructor might have used the original config if it was imported before patch?
        # No, patch handles that if we patch 'config'.
        # However, to be safe, we can reset the deque manually
        self.logic_engine.context_history = deque(maxlen=3)

    def tearDown(self):
        self.config_patcher.stop()

    def test_history_accumulation_and_window_size(self):
        """Verify history accumulates snapshots and respects window size."""
        start_time = 1000.0

        with patch('time.time', return_value=start_time):
            # First update - should trigger snapshot?
            # LogicEngine.last_history_update_time is 0 initially.
            # 1000 - 0 >= 1.0 -> Yes.
            self.logic_engine.update()
            self.assertEqual(len(self.logic_engine.context_history), 1)
            self.assertEqual(self.logic_engine.context_history[0]['timestamp'], start_time)

        # Second update - minimal time pass (no snapshot)
        with patch('time.time', return_value=start_time + 0.1):
            self.logic_engine.update()
            self.assertEqual(len(self.logic_engine.context_history), 1)

        # Third update - interval passed (snapshot)
        with patch('time.time', return_value=start_time + 1.1):
            self.logic_engine.update()
            self.assertEqual(len(self.logic_engine.context_history), 2)

        # Fourth update - interval passed (snapshot) -> Full (3)
        with patch('time.time', return_value=start_time + 2.2):
            self.logic_engine.update()
            self.assertEqual(len(self.logic_engine.context_history), 3)

        # Fifth update - interval passed (snapshot) -> Overflow (still 3, old dropped)
        with patch('time.time', return_value=start_time + 3.3):
            self.logic_engine.update()
            self.assertEqual(len(self.logic_engine.context_history), 3)
            # Verify the first item is now the one from time 1.1 (start_time was dropped)
            self.assertEqual(self.logic_engine.context_history[0]['timestamp'], start_time + 1.1)
            self.assertEqual(self.logic_engine.context_history[-1]['timestamp'], start_time + 3.3)

    def test_snapshot_content(self):
        """Verify the content of a history snapshot."""
        self.logic_engine.audio_level = 0.5
        self.logic_engine.video_activity = 10.0
        self.logic_engine.face_metrics = {"face_detected": True}
        self.logic_engine.set_mode("active")

        with patch('time.time', return_value=2000.0):
            self.logic_engine.update()

            self.assertEqual(len(self.logic_engine.context_history), 1)
            snap = self.logic_engine.context_history[0]

            self.assertEqual(snap['mode'], "active")
            self.assertEqual(snap['active_window'], "TestApp")
            self.assertEqual(snap['audio_level'], 0.5)
            self.assertEqual(snap['video_activity'], 10.0)
            self.assertEqual(snap['face_detected'], True)

    def test_lmm_data_preparation(self):
        """Verify history is included in LMM payload."""
        # Populate history
        self.logic_engine.context_history.append({"mock": "data"})

        # Prepare data
        self.logic_engine.last_video_frame = "mock_frame" # trigger valid payload

        # Mock cv2 to avoid actual encoding
        with patch('cv2.imencode', return_value=(True, b'mock')):
             data = self.logic_engine._prepare_lmm_data()

             self.assertIsNotNone(data)
             self.assertIn("history", data["user_context"])
             self.assertEqual(len(data["user_context"]["history"]), 1)
             self.assertEqual(data["user_context"]["history"][0]["mock"], "data")

if __name__ == '__main__':
    unittest.main()
