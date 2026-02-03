import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import numpy as np
import time

# Patch cv2 before import
sys.modules['cv2'] = MagicMock()
import cv2

# Patch config
import config

from sensors.video_sensor import VideoSensor

class TestVideoEcoSmart(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()

        # Setup VideoSensor
        self.config_patcher = patch.multiple(config,
            VIDEO_WAKE_THRESHOLD=5.0,
            VIDEO_ECO_HEARTBEAT_INTERVAL=1.0,
            BASELINE_POSTURE={}
        )
        self.config_patcher.start()

        # Mock cv2.CascadeClassifier
        self.mock_cascade = MagicMock()
        # Default behavior: return empty list (no faces)
        self.mock_cascade.detectMultiScale.return_value = []

        with patch('cv2.CascadeClassifier', return_value=self.mock_cascade):
            self.sensor = VideoSensor(camera_index=None, data_logger=self.mock_logger)

        self.sensor.face_cascade = self.mock_cascade
        self.sensor.calculate_raw_activity = MagicMock()

        self.dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)

        cv2.cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        cv2.resize.return_value = np.zeros((100, 100), dtype=np.uint8)

    def tearDown(self):
        self.config_patcher.stop()

    def test_smart_check_initialization(self):
        """Test that cache and timestamps are initialized."""
        self.assertEqual(self.sensor.last_face_check_time, 0)
        self.assertIn("face_detected", self.sensor.cached_face_metrics)
        self.assertFalse(self.sensor.cached_face_metrics["face_detected"])

    def test_high_activity_triggers_detection(self):
        """Test that high activity triggers face detection."""
        self.sensor.calculate_raw_activity.return_value = 10.0
        self.mock_cascade.detectMultiScale.reset_mock()
        # Ensure it returns a list so len() works
        self.mock_cascade.detectMultiScale.return_value = [(10, 10, 50, 50)]

        self.sensor.process_frame(self.dummy_frame)

        self.mock_cascade.detectMultiScale.assert_called_once()
        self.assertAlmostEqual(self.sensor.last_face_check_time, time.time(), delta=1.0)

    def test_low_activity_skips_detection(self):
        """Test that low activity skips detection if heartbeat hasn't expired."""
        # 1. Force a check first
        self.sensor.calculate_raw_activity.return_value = 10.0
        self.mock_cascade.detectMultiScale.return_value = [(10, 10, 50, 50)]
        self.sensor.process_frame(self.dummy_frame)
        self.mock_cascade.detectMultiScale.reset_mock()

        last_check = self.sensor.last_face_check_time

        # 2. Process next frame with Low Activity
        self.sensor.calculate_raw_activity.return_value = 2.0

        metrics = self.sensor.process_frame(self.dummy_frame)

        self.mock_cascade.detectMultiScale.assert_not_called()
        self.assertEqual(metrics["video_activity"], 2.0)

        # Verify metrics match what we set in step 1 (cached)
        self.assertTrue(metrics["face_detected"])
        self.assertEqual(metrics["face_count"], 1)

        self.assertEqual(self.sensor.last_face_check_time, last_check)

    def test_heartbeat_triggers_detection(self):
        """Test that heartbeat triggers detection even with low activity."""
        self.sensor.last_face_check_time = time.time() - 2.0

        self.sensor.calculate_raw_activity.return_value = 2.0
        self.mock_cascade.detectMultiScale.reset_mock()
        self.mock_cascade.detectMultiScale.return_value = []

        self.sensor.process_frame(self.dummy_frame)

        self.mock_cascade.detectMultiScale.assert_called_once()
        self.assertAlmostEqual(self.sensor.last_face_check_time, time.time(), delta=1.0)

    def test_cache_update_and_persistence(self):
        """Verify that cache is updated on detection and used on skip."""
        # 1. High activity, Face Detected
        self.sensor.calculate_raw_activity.return_value = 10.0
        self.mock_cascade.detectMultiScale.return_value = [(10, 10, 50, 50)]

        metrics = self.sensor.process_frame(self.dummy_frame)
        self.assertTrue(metrics["face_detected"])
        self.assertTrue(self.sensor.cached_face_metrics["face_detected"])

        # 2. Low activity, Skip Detection (use cache)
        self.sensor.calculate_raw_activity.return_value = 1.0
        self.mock_cascade.detectMultiScale.reset_mock()

        metrics_cached = self.sensor.process_frame(self.dummy_frame)

        self.mock_cascade.detectMultiScale.assert_not_called()
        self.assertTrue(metrics_cached["face_detected"])
        self.assertEqual(metrics_cached["face_count"], 1)

    def test_triggered_but_no_face_found(self):
        """Test scenario where detection runs but no face is found (should safe update cache)."""
        self.sensor.calculate_raw_activity.return_value = 10.0 # Trigger
        self.mock_cascade.detectMultiScale.return_value = [] # No faces

        # This should NOT raise KeyError
        metrics = self.sensor.process_frame(self.dummy_frame)

        self.assertFalse(metrics["face_detected"])
        self.assertEqual(metrics["face_count"], 0)
        self.assertEqual(metrics["face_size_ratio"], 0.0)

        # Verify cache was updated to 'no face'
        self.assertFalse(self.sensor.cached_face_metrics["face_detected"])
        self.assertEqual(self.sensor.cached_face_metrics["face_count"], 0)

if __name__ == '__main__':
    unittest.main()
