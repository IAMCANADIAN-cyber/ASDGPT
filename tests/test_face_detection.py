import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import cv2
from sensors.video_sensor import VideoSensor

class TestFaceDetection(unittest.TestCase):
    def setUp(self):
        # Create a mock logger
        self.mock_logger = MagicMock()
        # Initialize VideoSensor with mocked logger and camera index (doesn't matter since we mock capture)
        # We need to mock cv2.CascadeClassifier before initializing VideoSensor because it loads it in __init__
        with patch('cv2.CascadeClassifier') as MockCascade:
            self.mock_cascade_instance = MockCascade.return_value
            self.video_sensor = VideoSensor(camera_index=0, data_logger=self.mock_logger)
            # Ensure the sensor uses our mock instance
            self.video_sensor.face_cascade = self.mock_cascade_instance

    def test_no_face_detected(self):
        # Setup mock to return no faces
        # detectMultiScale returns a list of rectangles (x, y, w, h)
        # Empty tuple or list means no faces
        self.mock_cascade_instance.detectMultiScale.return_value = ()

        # Create a dummy frame (black image)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # Run analysis
        metrics = self.video_sensor.analyze_frame(frame)

        # Assertions
        self.assertFalse(metrics['face_detected'])
        self.assertEqual(metrics['face_count'], 0)
        self.assertEqual(metrics['face_locations'], [])

        # Verify conversion to grayscale happened
        # We can't easily check cv2.cvtColor call without patching cv2, but we can assume it worked if no error.

    def test_face_detected(self):
        # Setup mock to return one face: (x=10, y=10, w=20, h=20)
        # It usually returns a numpy array or tuple of arrays
        self.mock_cascade_instance.detectMultiScale.return_value = np.array([[10, 10, 20, 20]])

        # Create a dummy frame
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # Run analysis
        metrics = self.video_sensor.analyze_frame(frame)

        # Assertions
        self.assertTrue(metrics['face_detected'])
        self.assertEqual(metrics['face_count'], 1)
        self.assertEqual(metrics['face_locations'], [[10, 10, 20, 20]])

    def test_analyze_frame_with_none(self):
        metrics = self.video_sensor.analyze_frame(None)
        # Expect default metrics with False
        self.assertFalse(metrics['face_detected'])
        self.assertEqual(metrics['face_count'], 0)

    def test_analyze_frame_exception(self):
        # Make detectMultiScale raise an exception
        self.mock_cascade_instance.detectMultiScale.side_effect = Exception("OpenCV Error")

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metrics = self.video_sensor.analyze_frame(frame)

        # Should handle exception gracefully and return default metrics
        self.assertFalse(metrics['face_detected'])
        # Should have logged error
        self.mock_logger.log_error.assert_called()

if __name__ == '__main__':
    unittest.main()
