import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import time
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from sensors.video_sensor import VideoSensor

class TestVideoEcoSmart(unittest.TestCase):
    def setUp(self):
        # Patch config values
        self.config_patcher = patch.multiple(config,
                                             VIDEO_WAKE_THRESHOLD=5.0,
                                             VIDEO_ECO_HEARTBEAT_INTERVAL=1.0,
                                             BASELINE_POSTURE={},
                                             create=True)
        self.config_patcher.start()

        self.sensor = VideoSensor(camera_index=None)

        # Mock internal cascades to avoid OpenCV errors or actual detection
        self.sensor.face_cascade = MagicMock()
        self.sensor.eye_cascade = MagicMock()
        self.sensor.eye_cascade.empty.return_value = False

        # Reset state
        self.sensor.last_face_check_time = 0

    def tearDown(self):
        self.config_patcher.stop()

    def test_high_activity_triggers_detection(self):
        """Test that activity > threshold triggers face detection."""
        # Setup: Mock activity to be High (10.0 > 5.0)
        self.sensor.calculate_raw_activity = MagicMock(return_value=10.0)

        # Mock detectMultiScale to return empty list (no face, but detection ran)
        self.sensor.face_cascade.detectMultiScale.return_value = []

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.sensor.process_frame(frame)

        # Assert detection was called
        self.sensor.face_cascade.detectMultiScale.assert_called_once()
        # Assert timestamp updated
        self.assertNotEqual(self.sensor.last_face_check_time, 0)

    def test_low_activity_skips_detection(self):
        """Test that activity < threshold AND recent check skips detection."""
        # Setup: Mock activity to be Low (1.0 < 5.0)
        self.sensor.calculate_raw_activity = MagicMock(return_value=1.0)

        # Set last check to NOW (so heartbeat not expired)
        self.sensor.last_face_check_time = time.time()

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.sensor.process_frame(frame)

        # Assert detection was SKIPPED
        self.sensor.face_cascade.detectMultiScale.assert_not_called()

    def test_heartbeat_triggers_detection_even_with_low_activity(self):
        """Test that heartbeat expiry triggers detection even if activity is low."""
        # Setup: Low activity
        self.sensor.calculate_raw_activity = MagicMock(return_value=1.0)

        # Set last check to OLD time (2.0s ago > 1.0s interval)
        self.sensor.last_face_check_time = time.time() - 2.0

        self.sensor.face_cascade.detectMultiScale.return_value = []

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.sensor.process_frame(frame)

        # Assert detection was CALLED
        self.sensor.face_cascade.detectMultiScale.assert_called_once()

    def test_cached_metrics_consistency(self):
        """Test that when detection is skipped, cached metrics are used but activity is updated."""
        # 1. First Pass: Trigger Detection
        self.sensor.calculate_raw_activity = MagicMock(return_value=10.0)

        # Mock a face found
        # (x, y, w, h)
        fake_face = (10, 10, 50, 50)
        self.sensor.face_cascade.detectMultiScale.return_value = [fake_face]
        # Allow detectMultiScale to return something valid for MagicMock default
        # (Already set return_value above)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metrics1 = self.sensor.process_frame(frame)

        self.assertTrue(metrics1["face_detected"])
        self.assertEqual(metrics1["video_activity"], 10.0)
        self.assertEqual(metrics1["face_locations"], [[10, 10, 50, 50]])

        # 2. Second Pass: Skip Detection (Low Activity)
        self.sensor.face_cascade.detectMultiScale.reset_mock()
        self.sensor.calculate_raw_activity = MagicMock(return_value=1.0)
        # Ensure heartbeat logic doesn't trigger (it shouldn't, we just ran it)
        # We assume execution is fast enough that time.time() - last < 1.0

        metrics2 = self.sensor.process_frame(frame)

        # Verify detection skipped
        self.sensor.face_cascade.detectMultiScale.assert_not_called()

        # Verify metrics:
        # Should still report face detected (from cache)
        self.assertTrue(metrics2["face_detected"])
        # Activity should be NEW value
        self.assertEqual(metrics2["video_activity"], 1.0)
        # Timestamp should be NEW
        self.assertNotEqual(metrics1["timestamp"], metrics2["timestamp"])
        # Face data should match old data
        self.assertEqual(metrics2["face_locations"], metrics1["face_locations"])

if __name__ == '__main__':
    unittest.main()
