import unittest
from unittest.mock import MagicMock, patch
import time
import numpy as np
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import config

# Patch cv2 before importing VideoSensor
with patch('cv2.CascadeClassifier') as MockCascade:
    from sensors.video_sensor import VideoSensor

class TestVideoEcoSmart(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()

        # Patch cv2 functions used in process_frame
        self.cv2_patcher = patch('sensors.video_sensor.cv2')
        self.mock_cv2 = self.cv2_patcher.start()

        # Setup CascadeClassifier mock
        self.mock_cascade = MagicMock()
        self.mock_cv2.CascadeClassifier.return_value = self.mock_cascade
        self.mock_cascade.empty.return_value = False
        self.mock_cascade.detectMultiScale.return_value = [] # Default no faces

        # Setup standard frame mocks
        self.mock_cv2.cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        self.mock_cv2.resize.return_value = np.zeros((100, 100), dtype=np.uint8)

        # Initialize sensor
        self.sensor = VideoSensor(camera_index=None, data_logger=self.mock_logger)

        # Ensure we control config values
        self.config_patcher = patch.multiple(config,
                                             VIDEO_WAKE_THRESHOLD=5.0,
                                             VIDEO_ECO_HEARTBEAT_INTERVAL=1.0)
        self.config_patcher.start()

    def tearDown(self):
        self.cv2_patcher.stop()
        self.config_patcher.stop()

    def set_activity(self, value):
        """Helper to set the calculated activity level."""
        # calculate_raw_activity uses cv2.absdiff then np.mean
        # We mock cv2.absdiff to return an array that will result in 'value' when mean is taken
        self.mock_cv2.absdiff.return_value = np.full((100, 100), value, dtype=np.uint8)

    def test_high_activity_triggers_detection(self):
        """Test that high activity triggers face detection regardless of heartbeat."""
        self.set_activity(20.0) # > 5.0

        # Force a recent check time so heartbeat doesn't trigger it
        self.sensor.last_face_check_time = time.time()

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.sensor.last_frame = np.zeros((100, 100), dtype=np.uint8) # Ensure last_frame exists

        self.sensor.process_frame(frame)

        # Should have called detectMultiScale
        self.mock_cascade.detectMultiScale.assert_called()

    def test_low_activity_skips_detection(self):
        """Test that low activity skips detection if heartbeat hasn't expired."""
        self.set_activity(2.0) # < 5.0

        # Recent check
        self.sensor.last_face_check_time = time.time()

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.sensor.last_frame = np.zeros((100, 100), dtype=np.uint8)

        # Reset mock to clear init calls
        self.mock_cascade.detectMultiScale.reset_mock()

        metrics = self.sensor.process_frame(frame)

        # Should NOT have called detectMultiScale
        self.mock_cascade.detectMultiScale.assert_not_called()

        # Metrics should contain updated activity
        self.assertEqual(metrics["video_activity"], 2.0)
        # Timestamp should be current
        self.assertAlmostEqual(metrics["timestamp"], time.time(), delta=0.1)

    def test_heartbeat_triggers_detection(self):
        """Test that heartbeat triggers detection even with low activity."""
        self.set_activity(2.0) # < 5.0

        # Old check time (> 1.0s ago)
        self.sensor.last_face_check_time = time.time() - 2.0

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.sensor.last_frame = np.zeros((100, 100), dtype=np.uint8)

        self.mock_cascade.detectMultiScale.reset_mock()

        self.sensor.process_frame(frame)

        # Should have called detectMultiScale
        self.mock_cascade.detectMultiScale.assert_called()

        # Should have updated last_face_check_time
        self.assertAlmostEqual(self.sensor.last_face_check_time, time.time(), delta=0.1)

    def test_cache_structure(self):
        """Verify that cached metrics retain the face data."""
        # 1. First Pass: Detect a face
        self.set_activity(10.0) # Trigger detection
        self.sensor.last_face_check_time = 0

        # Mock a face being found
        # (x, y, w, h)
        fake_face = [(50, 50, 50, 50)]
        self.mock_cascade.detectMultiScale.return_value = fake_face

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.sensor.last_frame = np.zeros((100, 100), dtype=np.uint8)

        metrics1 = self.sensor.process_frame(frame)
        self.assertTrue(metrics1["face_detected"])
        self.assertEqual(metrics1["face_count"], 1)

        # 2. Second Pass: Low activity, use cache
        self.set_activity(1.0)
        self.mock_cascade.detectMultiScale.reset_mock()

        # process_frame should use cache now (last_face_check_time was just updated)
        metrics2 = self.sensor.process_frame(frame)

        self.mock_cascade.detectMultiScale.assert_not_called()

        # Should still show face detected (from cache)
        self.assertTrue(metrics2["face_detected"])
        self.assertEqual(metrics2["face_count"], 1)
        # Activity should be new
        self.assertEqual(metrics2["video_activity"], 1.0)

if __name__ == '__main__':
    unittest.main()
