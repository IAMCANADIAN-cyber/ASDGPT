import unittest
import numpy as np
import cv2
from sensors.video_sensor import VideoSensor

class TestVideoFeatures(unittest.TestCase):
    def setUp(self):
        # Initialize without camera
        self.sensor = VideoSensor(camera_index=None)

        # Override cascade with a mock if needed, but we can try to use a real one if available.
        # However, testing face detection without real images is hard.
        # We will test the metrics calculation logic given a mocked detection or a synthetic image.
        # Since I can't easily make a synthetic "face" that a Haar cascade recognizes reliably without assets,
        # I will mock the cascade classifier's detectMultiScale method to return known rectangles.

        # Mocking detectMultiScale
        from unittest.mock import MagicMock
        self.sensor.face_cascade = MagicMock()

        # Force Eco Mode check to pass (simulate recent face)
        import time
        self.sensor.last_face_detected_time = time.time()

    def test_metrics_no_face(self):
        self.sensor.face_cascade.detectMultiScale.return_value = []

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metrics = self.sensor.analyze_frame(frame)

        self.assertFalse(metrics['face_detected'])
        self.assertEqual(metrics['face_count'], 0)

    def test_metrics_one_face(self):
        # Mock one face: x=25, y=25, w=50, h=50 (Centered)
        # Note: detectMultiScale returns a list of rectangles (x, y, w, h)
        # It needs to return a structure that behaves like a list of numpy arrays or tuples
        # The code uses: for (x, y, w, h) in faces:
        self.sensor.face_cascade.detectMultiScale.return_value = [(25, 25, 50, 50)]

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metrics = self.sensor.analyze_frame(frame)

        self.assertTrue(metrics['face_detected'])
        self.assertEqual(metrics['face_count'], 1)
        self.assertAlmostEqual(metrics['face_size_ratio'], 0.5) # 50 / 100
        self.assertAlmostEqual(metrics['horizontal_position'], 0.5) # (25 + 25) / 100
        self.assertAlmostEqual(metrics['vertical_position'], 0.5) # (25 + 25) / 100

    def test_metrics_posture_lean(self):
        # Face is larger (leaning in) and higher up (standing/tall?)
        self.sensor.face_cascade.detectMultiScale.return_value = [(20, 10, 60, 60)]

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metrics = self.sensor.analyze_frame(frame)

        self.assertAlmostEqual(metrics['face_size_ratio'], 0.6)
        self.assertAlmostEqual(metrics['vertical_position'], 0.4) # (10 + 30) / 100 = 0.4

if __name__ == '__main__':
    unittest.main()
