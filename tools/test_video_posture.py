import sys
import os
import unittest
from unittest.mock import MagicMock
import numpy as np
import cv2

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sensors.video_sensor import VideoSensor

class TestVideoSensorPosture(unittest.TestCase):
    def setUp(self):
        self.sensor = VideoSensor(camera_index=None, data_logger=MagicMock())
        # Mock the cascade classifier to avoid loading the real one
        self.sensor.face_cascade = MagicMock()

    def test_posture_metrics_calculation(self):
        # Create a dummy frame (100x100)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # Mock detection: Face at x=25, y=25, w=50, h=50
        # This is centered in 100x100
        # Center: (50, 50) -> 0.5, 0.5
        # Area: 2500 -> Ratio: 0.25
        self.sensor.face_cascade.detectMultiScale.return_value = [[25, 25, 50, 50]]

        metrics = self.sensor.analyze_frame(frame)

        print(f"Metrics: {metrics}")

        # Basic assertions (existing behavior)
        self.assertTrue(metrics["face_detected"])
        self.assertEqual(metrics["face_count"], 1)

        # New assertions - Strict checks
        self.assertIn("face_size_ratio", metrics)
        self.assertAlmostEqual(metrics["face_size_ratio"], 0.25)

        self.assertIn("horizontal_position", metrics)
        self.assertAlmostEqual(metrics["horizontal_position"], 0.5)

        self.assertIn("vertical_position", metrics)
        self.assertAlmostEqual(metrics["vertical_position"], 0.5)

    def test_posture_leaning_in(self):
        # Face fills almost entire screen
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.sensor.face_cascade.detectMultiScale.return_value = [[10, 10, 80, 80]]

        metrics = self.sensor.analyze_frame(frame)

        self.assertIn("face_size_ratio", metrics)
        # 6400 / 10000 = 0.64
        self.assertAlmostEqual(metrics["face_size_ratio"], 0.64)

    def test_posture_slouching(self):
        # Face at bottom
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # x=25, y=60, w=50, h=50
        # Center Y = 60 + 25 = 85 -> 0.85
        self.sensor.face_cascade.detectMultiScale.return_value = [[25, 60, 50, 50]]

        metrics = self.sensor.analyze_frame(frame)

        self.assertIn("vertical_position", metrics)
        self.assertAlmostEqual(metrics["vertical_position"], 0.85)

    def test_no_face_detected(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.sensor.face_cascade.detectMultiScale.return_value = []

        metrics = self.sensor.analyze_frame(frame)

        self.assertFalse(metrics["face_detected"])
        self.assertEqual(metrics["face_count"], 0)
        self.assertNotIn("face_size_ratio", metrics)
        self.assertNotIn("vertical_position", metrics)
        self.assertNotIn("horizontal_position", metrics)

if __name__ == '__main__':
    unittest.main()
