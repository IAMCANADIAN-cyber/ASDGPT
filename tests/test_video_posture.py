
import unittest
import numpy as np
from unittest.mock import MagicMock
import sys

# Ensure sensors module can be imported
from sensors.video_sensor import VideoSensor

class TestVideoPosture(unittest.TestCase):
    def setUp(self):
        # We can pass camera_index=None to avoid opening the camera,
        # but VideoSensor might still try to init, so we mock VideoCapture if needed.
        # However, we only care about analyze_frame logic which uses self.face_cascade.

        # We need to ensure VideoSensor doesn't crash on init if camera 0 is missing.
        # It handles it by setting self.cap = None.
        self.sensor = VideoSensor(camera_index=None)

        # Mock the cascade to return deterministic values
        self.sensor.face_cascade = MagicMock()
        # Mock empty to return False so it thinks it's a valid cascade
        self.sensor.face_cascade.empty.return_value = False

    def test_posture_neutral(self):
        # Frame size 100x100
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # x=30, y=30, w=30, h=30
        # Ratio: 0.3 (Neutral range)
        # Vert: 30 + 15 = 45 -> 0.45 (Neutral range)
        self.sensor.face_cascade.detectMultiScale.return_value = [[30, 30, 30, 30]]

        metrics = self.sensor.analyze_frame(frame)

        self.assertTrue(metrics["face_detected"])
        self.assertAlmostEqual(metrics["face_size_ratio"], 0.3)
        self.assertEqual(metrics["posture_state"], "neutral")

    def test_posture_leaning_in(self):
        # Face fills almost entire screen
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # w=80 -> Ratio 0.8 (> 0.45)
        self.sensor.face_cascade.detectMultiScale.return_value = [[10, 10, 80, 80]]

        metrics = self.sensor.analyze_frame(frame)

        self.assertAlmostEqual(metrics["face_size_ratio"], 0.8)
        self.assertEqual(metrics["posture_state"], "leaning_forward")

    def test_posture_leaning_back(self):
        # Face is very small
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # w=10 -> Ratio 0.1 (< 0.15)
        self.sensor.face_cascade.detectMultiScale.return_value = [[45, 45, 10, 10]]

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

        self.assertAlmostEqual(metrics["vertical_position"], 0.85)
        # Note: Size is 0.5 (> 0.45) which triggers leaning_forward in current logic?
        # Let's check logic order in VideoSensor:
        # if ratio > 0.45: leaning_forward
        # elif ratio < 0.15: leaning_back
        # elif vert > 0.65: slouching
        # So if ratio is 0.5, it will be leaning_forward!

        # In current implementation of VideoSensor, ratio checks come first.
        # To test slouching, we need ratio to be within neutral bounds (0.15 - 0.45)

        # So for this test to be correct for SLOUCHING, we need a smaller face.
        # w=30 (0.3 ratio) which is neutral size.
        # y=70, h=30 -> Center Y = 70 + 15 = 85 (0.85)

        self.sensor.face_cascade.detectMultiScale.return_value = [[35, 70, 30, 30]]
        metrics = self.sensor.analyze_frame(frame)
        self.assertEqual(metrics["posture_state"], "slouching")

    def test_math_fix_verification(self):
        # The specific case from the "fix" branch that I want to ensure I covered
        # It was asserting ratio 0.5 for width 50 on 100px frame.
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Width 50 on 100px frame -> 0.5
        self.sensor.face_cascade.detectMultiScale.return_value = [[25, 25, 50, 50]]
        metrics = self.sensor.analyze_frame(frame)
        self.assertAlmostEqual(metrics["face_size_ratio"], 0.5)

if __name__ == '__main__':
    unittest.main()
