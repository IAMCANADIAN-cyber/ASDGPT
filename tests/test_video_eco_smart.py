
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# We need to ensure config has the new attribute if we are testing it before modifying video_sensor
# But step 1 already added it to config.py.
import config
from sensors.video_sensor import VideoSensor

class TestVideoEcoSmart(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        # Mock cv2.CascadeClassifier before VideoSensor init
        with patch('cv2.CascadeClassifier') as MockCascade:
            self.mock_cascade = MockCascade.return_value
            self.mock_cascade.empty.return_value = False
            self.video_sensor = VideoSensor(camera_index=None, data_logger=self.logger)
            # Ensure face_cascade is our mock
            self.video_sensor.face_cascade = self.mock_cascade
            # We don't care about eye cascade for this test

    def test_smart_check_wakes_on_activity(self):
        """
        Test that face detection runs when activity exceeds threshold.
        """
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # High activity
        with patch.object(self.video_sensor, 'calculate_raw_activity', return_value=50.0): # > 5.0 (default threshold)
             # Mock last_face_check_time to be recent so time check implies SKIP, but activity implies RUN
             self.video_sensor.last_face_check_time = time.time()

             self.video_sensor.process_frame(frame)

             # Assert detectMultiScale was called
             self.assertTrue(self.mock_cascade.detectMultiScale.called)

    def test_smart_check_skips_low_activity(self):
        """
        Test that face detection is skipped when activity is low and time is short.
        """
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Low activity
        with patch.object(self.video_sensor, 'calculate_raw_activity', return_value=1.0): # < 5.0
             # Recent check
             self.video_sensor.last_face_check_time = time.time()

             self.video_sensor.process_frame(frame)

             # Assert detectMultiScale was NOT called
             self.assertFalse(self.mock_cascade.detectMultiScale.called)

    def test_smart_check_wakes_on_heartbeat(self):
        """
        Test that face detection runs when heartbeat expires, even if activity is low.
        """
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Low activity
        with patch.object(self.video_sensor, 'calculate_raw_activity', return_value=1.0):
             # Old check (beyond 1.0s heartbeat)
             self.video_sensor.last_face_check_time = time.time() - 2.0

             self.video_sensor.process_frame(frame)

             # Assert detectMultiScale was called
             self.assertTrue(self.mock_cascade.detectMultiScale.called)

    def test_cached_metrics_returned(self):
        """
        Test that when skipped, cached metrics are returned with updated activity/timestamp.
        """
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Setup initial cached metrics
        self.video_sensor.cached_face_metrics = {
            "face_detected": True,
            "face_count": 1,
            "face_locations": [[10, 10, 50, 50]],
            "face_size_ratio": 0.1,
            "vertical_position": 0.5,
            "horizontal_position": 0.5,
            "face_roll_angle": 0.0,
            "posture_state": "neutral",
            "timestamp": 1000.0,
            "video_activity": 50.0,
            "normalized_activity": 1.0
        }

        with patch.object(self.video_sensor, 'calculate_raw_activity', return_value=2.0): # Low activity
             self.video_sensor.last_face_check_time = time.time() # Recent

             metrics = self.video_sensor.process_frame(frame)

             # Should be cached metrics, but updated timestamp and activity
             self.assertEqual(metrics["face_detected"], True)
             self.assertEqual(metrics["video_activity"], 2.0)
             self.assertNotEqual(metrics["timestamp"], 1000.0)
             self.assertFalse(self.mock_cascade.detectMultiScale.called)

if __name__ == '__main__':
    unittest.main()
