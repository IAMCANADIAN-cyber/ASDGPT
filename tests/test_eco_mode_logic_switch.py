import unittest
from unittest.mock import MagicMock, patch
import sys
import numpy as np

# Patch hardware dependencies BEFORE importing main
sys.modules['pystray'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['keyboard'] = MagicMock()

import config
from main import Application
from sensors.video_sensor import VideoSensor

class TestEcoModeLogicSwitch(unittest.TestCase):
    def setUp(self):
        # --- Setup Application Mocks ---
        self.mock_logic_engine = MagicMock()
        self.mock_video_sensor = MagicMock()
        self.mock_logger = MagicMock()

        self.patchers = []
        p1 = patch('main.VideoSensor', return_value=self.mock_video_sensor)
        p2 = patch('main.AudioSensor', MagicMock())
        p3 = patch('main.LMMInterface', MagicMock())
        p4 = patch('main.LogicEngine', return_value=self.mock_logic_engine)
        p5 = patch('main.InterventionEngine', MagicMock())
        p6 = patch('main.ACRTrayIcon', MagicMock())
        p7 = patch('main.DataLogger', return_value=self.mock_logger)
        p8 = patch.dict(sys.modules, {'keyboard': MagicMock()})
        p9 = patch('main.WindowSensor', MagicMock())

        self.patchers.extend([p1, p2, p3, p4, p5, p6, p7, p8, p9])
        for p in self.patchers:
            p.start()

        self.app = Application()
        self.app.logic_engine = self.mock_logic_engine

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        if self.app:
            self.app.quit_application()

    def test_should_run_face_detection_active_face(self):
        """Should always run face detection if face currently detected."""
        self.mock_logic_engine.is_face_detected.return_value = True
        self.app.face_check_counter = 100 # Random value

        result = self.app._should_run_face_detection()

        self.assertTrue(result)
        self.assertEqual(self.app.face_check_counter, 0) # Should reset

    def test_should_run_face_detection_high_activity(self):
        """Should run face detection if activity is high (waking up)."""
        self.mock_logic_engine.is_face_detected.return_value = False
        self.mock_logic_engine.video_activity = config.VIDEO_WAKE_THRESHOLD + 1.0
        self.app.face_check_counter = 100

        result = self.app._should_run_face_detection()

        self.assertTrue(result)
        self.assertEqual(self.app.face_check_counter, 0) # Should reset

    def test_should_run_face_detection_eco_skipping(self):
        """Should skip face detection in eco mode until interval hit."""
        self.mock_logic_engine.is_face_detected.return_value = False
        self.mock_logic_engine.video_activity = 0.0
        self.app.face_check_counter = 0

        # Interval is 5 (default in config if not mocked, but we assume 5)
        # config.VIDEO_ECO_FACE_CHECK_INTERVAL defaults to 5 if we didn't mock config

        # Frame 1: Counter -> 1. 1 % 5 != 0 -> False
        self.assertFalse(self.app._should_run_face_detection())
        self.assertEqual(self.app.face_check_counter, 1)

        # Frame 2: Counter -> 2. False
        self.assertFalse(self.app._should_run_face_detection())
        self.assertEqual(self.app.face_check_counter, 2)

        # Frame 3: Counter -> 3. False
        self.assertFalse(self.app._should_run_face_detection())

        # Frame 4: Counter -> 4. False
        self.assertFalse(self.app._should_run_face_detection())

        # Frame 5: Counter -> 5. 5 % 5 == 0 -> True
        self.assertTrue(self.app._should_run_face_detection())
        self.assertEqual(self.app.face_check_counter, 5)

        # Frame 6: Counter -> 6. False
        self.assertFalse(self.app._should_run_face_detection())


class TestVideoSensorSkipping(unittest.TestCase):
    def setUp(self):
        # We need to test the actual VideoSensor class, not a mock
        self.mock_logger = MagicMock()
        # Mock cv2 inside VideoSensor logic if possible, or use real cv2 but mock methods
        # To avoid opening camera, we pass camera_index=None (supported by our code)
        self.sensor = VideoSensor(camera_index=None, data_logger=self.mock_logger)

        # Mock the CascadeClassifier
        self.sensor.face_cascade = MagicMock()
        self.sensor.face_cascade.detectMultiScale.return_value = [] # No faces by default

        # Mock eye cascade to avoid errors
        self.sensor.eye_cascade = MagicMock()

    def test_process_frame_respects_flag(self):
        """VideoSensor.process_frame should skip detectMultiScale when flag is False."""
        # Create a dummy frame (100x100 black image)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # 1. Run with True
        self.sensor.process_frame(frame, run_face_detection=True)
        self.sensor.face_cascade.detectMultiScale.assert_called()
        self.sensor.face_cascade.detectMultiScale.reset_mock()

        # 2. Run with False
        metrics = self.sensor.process_frame(frame, run_face_detection=False)
        self.sensor.face_cascade.detectMultiScale.assert_not_called()

        # Assert metrics are safe/default
        self.assertFalse(metrics["face_detected"])
        self.assertEqual(metrics["face_count"], 0)

        # Activity should still be calculated
        # (It will be 0 since frame is constant 0s and last_frame will be 0s)
        self.assertIn("video_activity", metrics)

    def test_process_frame_activity_calculation(self):
        """VideoSensor.process_frame should calculate activity even if skipping face detection."""
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 255 # White frame

        # Init with frame1
        self.sensor.process_frame(frame1, run_face_detection=False)

        # Process frame2 (High diff)
        metrics = self.sensor.process_frame(frame2, run_face_detection=False)

        self.assertGreater(metrics["video_activity"], 0)
        self.sensor.face_cascade.detectMultiScale.assert_not_called()

if __name__ == '__main__':
    unittest.main()
