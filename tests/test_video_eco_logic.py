import unittest
from unittest.mock import MagicMock, patch, call
import time
import numpy as np
import sys

# Patch dependencies before imports
sys.modules['cv2'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['keyboard'] = MagicMock()

import config
from core.logic_engine import LogicEngine
from sensors.video_sensor import VideoSensor

class TestVideoEcoLogic(unittest.TestCase):

    def setUp(self):
        # Mock VideoSensor methods
        self.mock_video_sensor = MagicMock()
        self.mock_video_sensor.process_frame.return_value = {
            "video_activity": 10.0,
            "face_detected": False,
            "timestamp": time.time()
        }

        # Initialize LogicEngine with mocked sensor
        self.logic_engine = LogicEngine(video_sensor=self.mock_video_sensor)
        self.logic_engine.video_activity_threshold_high = 20.0

    def test_video_sensor_skip_logic(self):
        """Verify VideoSensor.process_frame respects skip_face_detection flag."""
        # Use real VideoSensor but mock cv2 inside it
        with patch('sensors.video_sensor.cv2') as mock_cv2:
            # Setup mocks
            mock_cv2.cvtColor.return_value = np.zeros((100,100), dtype=np.uint8)
            mock_cv2.resize.return_value = np.zeros((100,100), dtype=np.uint8)
            mock_cv2.absdiff.return_value = np.zeros((100,100), dtype=np.uint8)
            mock_cv2.mean.return_value = 10.0

            # Create instance (mock cascades loading to avoid file errors)
            with patch('os.path.exists', return_value=True):
                 with patch('cv2.CascadeClassifier', MagicMock()):
                     sensor = VideoSensor(camera_index=None)
                     sensor.face_cascade = MagicMock()

                     # Test with skip=True
                     frame = np.zeros((480, 640, 3), dtype=np.uint8)
                     metrics = sensor.process_frame(frame, skip_face_detection=True)

                     self.assertTrue(metrics.get("face_detection_skipped"))
                     sensor.face_cascade.detectMultiScale.assert_not_called()

                     # Test with skip=False
                     metrics = sensor.process_frame(frame, skip_face_detection=False)
                     self.assertFalse(metrics.get("face_detection_skipped", False))
                     sensor.face_cascade.detectMultiScale.assert_called_once()

    def test_video_sensor_skip_override(self):
        """Verify VideoSensor overrides skip if activity > threshold."""
        # Use partial mocking to only override calculation
        with patch('sensors.video_sensor.cv2') as mock_cv2:
            mock_cv2.cvtColor.return_value = np.zeros((100,100), dtype=np.uint8)

            with patch('os.path.exists', return_value=True):
                 with patch('cv2.CascadeClassifier', MagicMock()):
                     sensor = VideoSensor(camera_index=None)
                     sensor.face_cascade = MagicMock()

                     # Mock calculate_raw_activity to return high activity
                     sensor.calculate_raw_activity = MagicMock(return_value=25.0)

                     frame = np.zeros((480, 640, 3), dtype=np.uint8)

                     # Pass skip=True, but threshold=20. Activity=25. Should NOT skip.
                     metrics = sensor.process_frame(frame, skip_face_detection=True, activity_threshold=20.0)

                     self.assertFalse(metrics.get("face_detection_skipped", False))
                     sensor.face_cascade.detectMultiScale.assert_called_once()

    def test_logic_engine_hierarchical_sensing_low_activity(self):
        """Test LogicEngine skips face detection when activity is low."""
        self.logic_engine.video_activity = 5.0 # Low activity
        self.logic_engine.last_face_check_time = time.time() # Just checked

        frame = np.zeros((100,100,3), dtype=np.uint8)
        self.logic_engine.process_video_data(frame)

        # Verify call args
        self.mock_video_sensor.process_frame.assert_called_with(
            frame,
            skip_face_detection=True,
            activity_threshold=20.0
        )

    def test_logic_engine_hierarchical_sensing_high_activity(self):
        """Test LogicEngine forces face detection when activity is high."""
        self.logic_engine.video_activity = 25.0 # High activity
        self.logic_engine.last_face_check_time = time.time() # Just checked

        frame = np.zeros((100,100,3), dtype=np.uint8)
        self.logic_engine.process_video_data(frame)

        # Verify call args
        self.mock_video_sensor.process_frame.assert_called_with(
            frame,
            skip_face_detection=False,
            activity_threshold=20.0
        )

    def test_logic_engine_hierarchical_sensing_heartbeat(self):
        """Test LogicEngine forces face detection on heartbeat (1s)."""
        self.logic_engine.video_activity = 5.0 # Low activity
        self.logic_engine.last_face_check_time = time.time() - 1.5 # 1.5s ago

        frame = np.zeros((100,100,3), dtype=np.uint8)
        self.logic_engine.process_video_data(frame)

        # Verify call args
        self.mock_video_sensor.process_frame.assert_called_with(
            frame,
            skip_face_detection=False,
            activity_threshold=20.0
        )

        # Verify heartbeat update (only if mock returns clean metric)
        # Note: logic engine updates time based on current_time in method,
        # so if we didn't mock metrics returned, it might not update logic engine state?
        # LogicEngine code:
        # if not metrics.get("face_detection_skipped", False):
        #    self.last_face_check_time = current_time

        # Our mock setup returns clean metrics (no skipped flag), so logic engine should update
        self.assertAlmostEqual(self.logic_engine.last_face_check_time, time.time(), delta=0.1)

    def test_logic_engine_state_persistence(self):
        """Verify LogicEngine persists old face metrics when skipping detection."""
        # 1. Set initial state (Face Detected)
        self.logic_engine.face_metrics = {"face_detected": True, "face_count": 1}
        self.logic_engine.video_activity = 5.0
        self.logic_engine.last_face_check_time = time.time()

        # 2. Mock sensor to return skipped
        self.mock_video_sensor.process_frame.return_value = {
            "video_activity": 5.0,
            "face_detection_skipped": True,
            "timestamp": time.time()
        }

        # 3. Process frame (Should skip)
        frame = np.zeros((100,100,3), dtype=np.uint8)
        self.logic_engine.process_video_data(frame)

        # 4. Verify state persisted
        self.assertTrue(self.logic_engine.face_metrics["face_detected"])
        self.assertEqual(self.logic_engine.face_metrics["face_count"], 1)

if __name__ == '__main__':
    unittest.main()
