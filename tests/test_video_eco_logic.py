import unittest
from unittest.mock import MagicMock, patch, ANY
import numpy as np
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from sensors.video_sensor import VideoSensor
import config

class TestVideoEcoLogic(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()

        # Patch config to ensure known thresholds
        self.config_patch = patch('sensors.video_sensor.config', autospec=True)
        self.mock_config = self.config_patch.start()
        self.mock_config.VIDEO_WAKE_THRESHOLD = 5.0
        # Assume we will add this new config
        self.mock_config.VIDEO_ECO_HEARTBEAT_INTERVAL = 1.0

        # Mock cv2
        self.cv2_patch = patch('sensors.video_sensor.cv2')
        self.mock_cv2 = self.cv2_patch.start()

        # Setup Cascade Mock
        self.mock_cascade = MagicMock()
        self.mock_cascade.empty.return_value = False
        self.mock_cascade.detectMultiScale.return_value = () # No faces by default
        self.mock_cv2.CascadeClassifier.return_value = self.mock_cascade
        self.mock_cv2.data.haarcascades = "/tmp/"

        # Setup cv2.absdiff and other helpers
        self.mock_cv2.cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        self.mock_cv2.resize.return_value = np.zeros((100, 100), dtype=np.uint8)
        self.mock_cv2.absdiff.return_value = np.zeros((100, 100), dtype=np.uint8)
        self.mock_cv2.mean.return_value = (0.0, 0.0, 0.0, 0.0)
        self.mock_cv2.COLOR_BGR2GRAY = 6

        self.sensor = VideoSensor(camera_index=None, data_logger=self.logger)
        # Manually inject cascades in case init logic bypassed them
        self.sensor.face_cascade = self.mock_cascade

    def tearDown(self):
        self.config_patch.stop()
        self.cv2_patch.stop()

    def test_smart_face_check_logic(self):
        """
        Verify that face detection is skipped when activity is low and skipped recently,
        but runs on heartbeat or high activity.
        """
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # 1. First call: Should ALWAYS run face detection (init)
        self.sensor.process_frame(frame)
        self.assertEqual(self.mock_cascade.detectMultiScale.call_count, 1, "First frame should run detection")

        # 2. Second call (Immediate, Low Activity): Should SKIP detection
        # Ensure activity is low
        self.sensor.calculate_raw_activity = MagicMock(return_value=0.0)

        self.sensor.process_frame(frame)
        self.assertEqual(self.mock_cascade.detectMultiScale.call_count, 1, "Low activity frame should skip detection")

        # 3. Third call (After 1.1s, Low Activity): Should RUN detection (Heartbeat)
        # We need to mock time.time()
        with patch('time.time') as mock_time:
            # First call was at t=0 (approx)
            # We simulate time advancing
            start_time = 1000.0

            # Reset sensor state relative to our mocked time
            self.sensor.last_face_check_time = start_time

            # Advance 0.5s (should skip)
            mock_time.return_value = start_time + 0.5
            self.sensor.process_frame(frame)
            self.assertEqual(self.mock_cascade.detectMultiScale.call_count, 1, "Should still skip at 0.5s")

            # Advance 1.1s (should run)
            mock_time.return_value = start_time + 1.1
            self.sensor.process_frame(frame)
            self.assertEqual(self.mock_cascade.detectMultiScale.call_count, 2, "Should run at 1.1s (Heartbeat)")

    def test_high_activity_wakes_detection(self):
        """
        Verify that high activity triggers immediate face detection.
        """
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # 1. First call (Init)
        self.sensor.process_frame(frame)
        self.assertEqual(self.mock_cascade.detectMultiScale.call_count, 1)

        # 2. Second call (Immediate, HIGH Activity)
        self.sensor.calculate_raw_activity = MagicMock(return_value=20.0) # > 5.0 Threshold

        self.sensor.process_frame(frame)
        self.assertEqual(self.mock_cascade.detectMultiScale.call_count, 2, "High activity should trigger detection")

    def test_cached_metrics_returned(self):
        """
        Verify that when detection is skipped, cached face metrics are returned.
        """
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Setup: First call finds a face
        # detectMultiScale returns a face rect
        self.mock_cascade.detectMultiScale.return_value = np.array([(10, 10, 50, 50)])

        metrics_1 = self.sensor.process_frame(frame)
        self.assertTrue(metrics_1["face_detected"])
        self.assertEqual(metrics_1["face_count"], 1)

        # Setup: Second call (Low Activity, Immediate) -> Skips detection
        self.sensor.calculate_raw_activity = MagicMock(return_value=0.0)
        # Reset mock to ensure it's NOT called
        self.mock_cascade.detectMultiScale.reset_mock()

        metrics_2 = self.sensor.process_frame(frame)

        # Assertions
        self.mock_cascade.detectMultiScale.assert_not_called()
        self.assertTrue(metrics_2["face_detected"], "Should return cached True state")
        self.assertEqual(metrics_2["face_count"], 1, "Should return cached count")
        self.assertEqual(metrics_2["face_size_ratio"], metrics_1["face_size_ratio"])

if __name__ == '__main__':
    unittest.main()
