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

        # Mock detection: Face at x=25, y=25, w=30, h=30 (Medium/Normal)
        # Ratio: 30/100 = 0.3 (Neutral range is 0.15 - 0.45)
        # Center: 25 + 15 = 40 -> 0.4 (Neutral range < 0.65)
        self.sensor.face_cascade.detectMultiScale.return_value = [[25, 25, 30, 30]]

        metrics = self.sensor.analyze_frame(frame)

        print(f"Metrics: {metrics}")

        # Basic assertions (existing behavior)
        self.assertTrue(metrics["face_detected"])
        self.assertEqual(metrics["face_count"], 1)

        # New assertions - Strict checks
        self.assertIn("face_size_ratio", metrics)
        self.assertAlmostEqual(metrics["face_size_ratio"], 0.3)

        self.assertIn("horizontal_position", metrics)
        self.assertAlmostEqual(metrics["horizontal_position"], 0.4)

        self.assertIn("vertical_position", metrics)
        self.assertAlmostEqual(metrics["vertical_position"], 0.4)

        # Posture check
        self.assertIn("posture_state", metrics)
        self.assertEqual(metrics["posture_state"], "neutral")

    def test_posture_leaning_in(self):
        # Face fills almost entire screen (Large)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.sensor.face_cascade.detectMultiScale.return_value = [[10, 10, 80, 80]]

        metrics = self.sensor.analyze_frame(frame)

        self.assertIn("face_size_ratio", metrics)
        self.assertAlmostEqual(metrics["face_size_ratio"], 0.8)
        self.assertEqual(metrics["posture_state"], "leaning_forward")

    def test_posture_leaning_back(self):
        # Face is very small (Far)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.sensor.face_cascade.detectMultiScale.return_value = [[45, 45, 10, 10]] # 0.1 ratio

        metrics = self.sensor.analyze_frame(frame)

        self.assertAlmostEqual(metrics["face_size_ratio"], 0.1)
        self.assertEqual(metrics["posture_state"], "leaning_back")

    def test_posture_slouching(self):
        # Face at bottom
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # x=25, y=60, w=50, h=50
        # Center Y = 60 + 25 = 85 -> 0.85 (> 0.65 threshold)
        self.sensor.face_cascade.detectMultiScale.return_value = [[25, 60, 50, 50]]

        metrics = self.sensor.analyze_frame(frame)

        self.assertIn("vertical_position", metrics)
        self.assertAlmostEqual(metrics["vertical_position"], 0.85)
        # Note: Size is 0.5 (> 0.45) so it might trigger leaning_forward depending on check order.
        # My implementation checked size first!
        # if metrics["face_size_ratio"] > 0.45: -> leaning_forward
        # Let's adjust test expectation OR implementation order.
        # Logic: Size > 0.45 = leaning_forward.
        # In this test case, size is 0.5. So it will be leaning_forward.

        # Let's make the face smaller for pure slouching test
        # Size 30 (0.3) -> Neutral size
        # Position 70 -> Center 85 (0.85) -> Slouching
        self.sensor.face_cascade.detectMultiScale.return_value = [[35, 70, 30, 30]]
        metrics = self.sensor.analyze_frame(frame)
        self.assertEqual(metrics["posture_state"], "slouching")

    def test_no_face_detected(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.sensor.face_cascade.detectMultiScale.return_value = []

        metrics = self.sensor.analyze_frame(frame)

        self.assertFalse(metrics["face_detected"])
        self.assertEqual(metrics["face_count"], 0)
        # These keys should exist but be 0.0, because analyze_frame always populates them
        self.assertEqual(metrics["face_size_ratio"], 0.0)
        self.assertEqual(metrics["vertical_position"], 0.0)
        self.assertEqual(metrics["horizontal_position"], 0.0)

if __name__ == '__main__':
    unittest.main()
