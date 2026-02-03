import unittest
from unittest.mock import MagicMock, patch
import sys
import numpy as np
import time

# Mock dependencies
sys.modules['cv2'] = MagicMock()
import cv2

import config
from sensors.video_sensor import VideoSensor

class TestVideoEcoLogicSensor(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()

        # Patch config values
        self.config_patcher = patch.multiple(config,
            VIDEO_WAKE_THRESHOLD=5.0,
            VIDEO_ECO_HEARTBEAT_INTERVAL=1.0,
            BASELINE_POSTURE={}
        )
        self.config_patcher.start()

        # Mock cv2 methods
        self.mock_cap = MagicMock()
        self.mock_cap.isOpened.return_value = True
        self.mock_cap.read.return_value = (True, np.zeros((100, 100, 3), dtype=np.uint8))

        cv2.VideoCapture.return_value = self.mock_cap
        cv2.cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        cv2.resize.return_value = np.zeros((100, 100), dtype=np.uint8)
        cv2.absdiff.return_value = np.zeros((100, 100), dtype=np.uint8)

        # Setup CascadeClassifier mock
        self.mock_cascade = MagicMock()
        self.mock_cascade.empty.return_value = False
        # Default: no faces
        self.mock_cascade.detectMultiScale.return_value = []
        cv2.CascadeClassifier.return_value = self.mock_cascade

        self.sensor = VideoSensor(camera_index=0, data_logger=self.mock_logger)

        # Manually set last_frame to enable activity calc
        self.sensor.last_frame = np.zeros((100, 100), dtype=np.uint8)

    def tearDown(self):
        self.config_patcher.stop()

    def test_high_activity_triggers_detection(self):
        """Test that high activity triggers face detection."""
        # Setup: High activity (mock raw_activity return)
        # VideoSensor.calculate_raw_activity is called internally.
        # We can mock it or mock cv2.absdiff result.
        # Let's mock calculate_raw_activity for easier control.

        with patch.object(self.sensor, 'calculate_raw_activity', return_value=50.0): # > 5.0
             frame = np.zeros((100, 100, 3), dtype=np.uint8)
             self.sensor.process_frame(frame)

             # Should have called detectMultiScale
             self.sensor.face_cascade.detectMultiScale.assert_called()
             # Should have updated last_face_check_time
             self.assertAlmostEqual(self.sensor.last_face_check_time, time.time(), delta=0.5)

    def test_low_activity_skips_detection(self):
        """Test that low activity skips detection if heartbeat hasn't elapsed."""
        # 1. Run once to set last_face_check_time
        with patch.object(self.sensor, 'calculate_raw_activity', return_value=50.0):
             self.sensor.process_frame(np.zeros((100, 100, 3), dtype=np.uint8))

        self.sensor.face_cascade.detectMultiScale.reset_mock()
        last_check = self.sensor.last_face_check_time

        # 2. Run again with low activity, immediately
        with patch.object(self.sensor, 'calculate_raw_activity', return_value=1.0): # < 5.0
             self.sensor.process_frame(np.zeros((100, 100, 3), dtype=np.uint8))

             # Should NOT have called detectMultiScale
             self.sensor.face_cascade.detectMultiScale.assert_not_called()
             # last_face_check_time should not change
             self.assertEqual(self.sensor.last_face_check_time, last_check)

    def test_heartbeat_triggers_detection(self):
        """Test that heartbeat triggers detection even with low activity."""
        # 1. Set last_face_check_time to old time
        self.sensor.last_face_check_time = time.time() - 2.0 # > 1.0s ago

        with patch.object(self.sensor, 'calculate_raw_activity', return_value=1.0): # Low activity
             self.sensor.process_frame(np.zeros((100, 100, 3), dtype=np.uint8))

             # Should have called detectMultiScale due to heartbeat
             self.sensor.face_cascade.detectMultiScale.assert_called()
             # Should have updated last_face_check_time
             self.assertAlmostEqual(self.sensor.last_face_check_time, time.time(), delta=0.5)

    def test_cache_usage(self):
        """Verify that cached metrics are returned when detection is skipped."""
        # 1. Setup cache with specific value
        self.sensor.cached_face_metrics["face_detected"] = True
        self.sensor.cached_face_metrics["face_count"] = 1
        self.sensor.last_face_check_time = time.time() # Fresh check

        with patch.object(self.sensor, 'calculate_raw_activity', return_value=1.0):
             metrics = self.sensor.process_frame(np.zeros((100, 100, 3), dtype=np.uint8))

             self.assertTrue(metrics["face_detected"])
             self.assertEqual(metrics["face_count"], 1)
             self.sensor.face_cascade.detectMultiScale.assert_not_called()

if __name__ == '__main__':
    unittest.main()
