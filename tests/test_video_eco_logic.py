import unittest
from unittest.mock import MagicMock, patch
import sys
import time

# Ensure we can import modules
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestVideoEcoLogic(unittest.TestCase):
    def setUp(self):
        # Patching dictionary for sys.modules
        self.modules_to_patch = {
            "cv2": MagicMock(),
            "numpy": MagicMock(),
        }
        self.patcher = patch.dict(sys.modules, self.modules_to_patch)
        self.patcher.start()

        # Mock config
        self.config_patcher = patch('config.VIDEO_WAKE_THRESHOLD', 5.0)
        self.config_patcher.start()

        # Reload VideoSensor to use mocked cv2
        if 'sensors.video_sensor' in sys.modules:
            del sys.modules['sensors.video_sensor']
        from sensors.video_sensor import VideoSensor
        self.VideoSensor = VideoSensor

        # Setup common mocks
        self.mock_cv2 = sys.modules["cv2"]
        self.mock_cv2.data.haarcascades = "/mock/path/"
        self.mock_cv2.CascadeClassifier = MagicMock()

        # Instantiate sensor
        with patch('os.path.exists', return_value=True):
            self.sensor = self.VideoSensor(camera_index=None)

    def tearDown(self):
        self.patcher.stop()
        self.config_patcher.stop()
        if 'sensors.video_sensor' in sys.modules:
            del sys.modules['sensors.video_sensor']

    def test_smart_face_check_high_activity(self):
        """Test that face detection runs when activity is high."""
        # Setup mocks
        self.sensor.calculate_raw_activity = MagicMock(return_value=10.0) # > 5.0
        self.sensor.face_cascade.detectMultiScale = MagicMock(return_value=[])

        # Run process_frame
        frame = MagicMock()
        self.sensor.process_frame(frame)

        # Assert detectMultiScale was called
        self.assertTrue(self.sensor.face_cascade.detectMultiScale.called)

    def test_smart_face_check_low_activity_no_recent_face(self):
        """Test that face detection is SKIPPED when activity is low and no recent face."""
        # Setup mocks
        self.sensor.calculate_raw_activity = MagicMock(return_value=2.0) # < 5.0
        self.sensor.last_face_detected_time = 0 # Long ago
        self.sensor.frame_count = 1 # Not a heartbeat (assuming % 30)
        self.sensor.face_cascade.detectMultiScale = MagicMock()

        # Run process_frame
        frame = MagicMock()
        metrics = self.sensor.process_frame(frame)

        # Assert detectMultiScale was NOT called
        self.assertFalse(self.sensor.face_cascade.detectMultiScale.called)
        self.assertFalse(metrics["face_detected"])

    def test_smart_face_check_heartbeat(self):
        """Test that face detection runs on heartbeat frame even if low activity."""
        # Setup mocks
        self.sensor.calculate_raw_activity = MagicMock(return_value=2.0) # < 5.0
        self.sensor.last_face_detected_time = 0
        self.sensor.frame_count = 29 # Next inc will be 30 (heartbeat)

        # NOTE: logic likely increments first, or check is on current count.
        # Plan says "Increment frame_count" then check.
        # So if we start at 29, it becomes 30.

        self.sensor.face_cascade.detectMultiScale = MagicMock(return_value=[])

        # Run process_frame
        frame = MagicMock()
        self.sensor.process_frame(frame)

        # Assert detectMultiScale WAS called
        self.assertTrue(self.sensor.face_cascade.detectMultiScale.called)

    def test_smart_face_check_hysteresis(self):
        """Test that face detection runs if face was recently detected."""
        # Setup mocks
        self.sensor.calculate_raw_activity = MagicMock(return_value=2.0) # < 5.0
        self.sensor.last_face_detected_time = time.time() - 1.0 # 1s ago (< 2s)
        self.sensor.frame_count = 1

        self.sensor.face_cascade.detectMultiScale = MagicMock(return_value=[])

        # Run process_frame
        frame = MagicMock()
        self.sensor.process_frame(frame)

        # Assert detectMultiScale WAS called
        self.assertTrue(self.sensor.face_cascade.detectMultiScale.called)
