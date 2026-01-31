
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import config
from sensors.video_sensor import VideoSensor

class TestVideoSensorEco(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        with patch('cv2.CascadeClassifier') as MockCascade:
            self.mock_cascade = MockCascade.return_value
            self.mock_cascade.empty.return_value = False
            self.video_sensor = VideoSensor(camera_index=None, data_logger=self.logger)
            self.video_sensor.face_cascade = self.mock_cascade
            # Disable eye cascade to simplify
            self.video_sensor.eye_cascade = None

        # Reset sensor state for each test
        self.video_sensor.last_frame = None
        self.video_sensor.last_face_detected_time = 0
        self.video_sensor.frame_count = 0

    def test_process_frame_high_activity(self):
        """Test that face detection runs when activity is high."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Mock high activity calculation
        # VideoSensor calls calculate_raw_activity internally
        # We can mock calculate_raw_activity to return high value
        self.video_sensor.calculate_raw_activity = MagicMock(return_value=config.VIDEO_WAKE_THRESHOLD + 10.0)

        self.video_sensor.process_frame(frame)

        # Should have called detectMultiScale
        self.mock_cascade.detectMultiScale.assert_called()

    def test_process_frame_low_activity_no_face(self):
        """Test that face detection is SKIPPED when activity is low and no recent face."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Mock low activity
        self.video_sensor.calculate_raw_activity = MagicMock(return_value=config.VIDEO_WAKE_THRESHOLD - 1.0)
        # Ensure last face was long ago
        self.video_sensor.last_face_detected_time = time.time() - 100

        # Reset mock calls
        self.mock_cascade.detectMultiScale.reset_mock()

        # Need to ensure frame_count is not a heartbeat frame (e.g. 0 might be skipped or not depending on impl)
        # Assuming heartbeat is % 5
        self.video_sensor.frame_count = 1

        metrics = self.video_sensor.process_frame(frame)

        # Should NOT have called detectMultiScale
        self.mock_cascade.detectMultiScale.assert_not_called()
        self.assertFalse(metrics["face_detected"])

        # Verify schema consistency (Reviewer concern)
        self.assertIn("face_detected", metrics)
        self.assertIn("face_count", metrics)
        self.assertIn("face_locations", metrics)
        self.assertIn("posture_state", metrics)

    def test_process_frame_low_activity_recent_face(self):
        """Test that face detection runs if face was seen recently, even if activity is low."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        self.video_sensor.calculate_raw_activity = MagicMock(return_value=config.VIDEO_WAKE_THRESHOLD - 1.0)
        # Recent face
        self.video_sensor.last_face_detected_time = time.time() - 2.0

        self.video_sensor.process_frame(frame)

        self.mock_cascade.detectMultiScale.assert_called()

    def test_process_frame_heartbeat(self):
        """Test that face detection runs on heartbeat frames even if idle."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        self.video_sensor.calculate_raw_activity = MagicMock(return_value=0.0)
        self.video_sensor.last_face_detected_time = 0

        # Assuming heartbeat is every 5th frame
        # process_frame increments frame_count by 1
        self.video_sensor.frame_count = 4

        self.video_sensor.process_frame(frame)

        self.mock_cascade.detectMultiScale.assert_called()

if __name__ == '__main__':
    unittest.main()
