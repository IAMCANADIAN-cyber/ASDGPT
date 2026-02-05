
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import math
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import config
from sensors.video_sensor import VideoSensor
from core.logic_engine import LogicEngine
from core.data_logger import DataLogger

class TestVideoMetrics(unittest.TestCase):
    def setUp(self):
        # Ensure consistent posture baseline for tests
        self.config_patcher = patch.object(config, 'BASELINE_POSTURE', {}, create=True)
        self.config_patcher.start()

        self.logger = MagicMock(spec=DataLogger)
        # Mock cv2.CascadeClassifier before VideoSensor init
        with patch('cv2.CascadeClassifier') as MockCascade:
            self.mock_cascade = MockCascade.return_value
            self.mock_cascade.empty.return_value = False
            self.video_sensor = VideoSensor(camera_index=None, data_logger=self.logger)
            # Ensure eye_cascade is also a mock (it's loaded inside init if found)
            # If it wasn't found (no file), it might be None. We force it to be our mock.
            self.video_sensor.eye_cascade = self.mock_cascade
            self.video_sensor.face_cascade = self.mock_cascade

    def tearDown(self):
        self.config_patcher.stop()

    def test_head_tilt_calculation(self):
        """
        Test that face_roll_angle is calculated correctly based on eye positions.
        """
        # Create a dummy frame (gray conversion happens inside process_frame)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Mock Face Detection: Return one face
        # x, y, w, h
        face_rect = (200, 100, 200, 200)

        # Mock Eye Detection
        # Eyes are relative to the ROI (face).
        # ROI is 200x200.
        # Let's simulate a 45 degree tilt.
        # Left eye (relative to face): (50, 100)
        # Right eye (relative to face): (150, 200) -> dy=100, dx=100 -> 45 degrees

        # Eye format: (ex, ey, ew, eh)
        eye1 = (50, 100, 30, 30)
        eye2 = (150, 200, 30, 30)

        # detectMultiScale is called twice: once for face, once for eyes
        # We need side_effect to return different results

        def detect_side_effect(image, **kwargs):
            # Check image shape to guess if it's full frame (face detect) or ROI (eye detect)
            if image.shape == (480, 640): # Full frame gray
                return np.array([face_rect])
            else: # ROI (face size is 200x200)
                return np.array([eye1, eye2])

        self.mock_cascade.detectMultiScale.side_effect = detect_side_effect

        metrics = self.video_sensor.process_frame(frame)

        self.assertTrue(metrics["face_detected"])
        self.assertIn("face_roll_angle", metrics)

        # Calculate expected angle
        # Centers:
        # Left: 50+15, 100+15 = 65, 115
        # Right: 150+15, 200+15 = 165, 215
        # dy = 100, dx = 100 -> 45 degrees
        self.assertAlmostEqual(metrics["face_roll_angle"], 45.0, delta=1.0)

        # 45 > 20 -> Should be tilted_right (positive angle)
        self.assertEqual(metrics["posture_state"], "tilted_right")

    def test_head_tilt_left(self):
        """
        Test tilt in the other direction (negative angle).
        """
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        face_rect = (200, 100, 200, 200)

        # Left eye (image left, smaller x): higher y (lower value)
        # Right eye (image right, larger x): lower y (higher value) -> positive angle

        # To get negative angle (tilted left), right eye must be higher (smaller y) than left eye.
        # Left eye: (50, 150)
        # Right eye: (150, 50)
        # dy = 50 - 150 = -100
        # dx = 150 - 50 = 100
        # atan2(-100, 100) = -45 deg

        eye1 = (50, 150, 30, 30)
        eye2 = (150, 50, 30, 30)

        def detect_side_effect(image, **kwargs):
            if image.shape == (480, 640):
                return np.array([face_rect])
            else:
                return np.array([eye1, eye2])

        self.mock_cascade.detectMultiScale.side_effect = detect_side_effect

        metrics = self.video_sensor.process_frame(frame)

        self.assertAlmostEqual(metrics["face_roll_angle"], -45.0, delta=1.0)
        self.assertEqual(metrics["posture_state"], "tilted_left")

    def test_logic_engine_integration(self):
        """
        Verify LogicEngine correctly propagates the new metrics.
        """
        mock_sensor = MagicMock()
        mock_sensor.process_frame.return_value = {
            "face_detected": True,
            "face_count": 1,
            "face_roll_angle": 15.0,
            "posture_state": "slouching",
            "vertical_position": 0.8,
            "normalized_activity": 0.5,
            "video_activity": 20.0
        }

        engine = LogicEngine(video_sensor=mock_sensor, logger=self.logger)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        engine.process_video_data(frame)

        analysis = engine.video_analysis

        self.assertEqual(analysis.get("face_roll_angle"), 15.0)
        self.assertEqual(analysis.get("posture_state"), "slouching")
        self.assertEqual(analysis.get("vertical_position"), 0.8)
        self.assertEqual(analysis.get("normalized_activity"), 0.5)

    def test_posture_leaning_forward(self):
        # Frame 100x100
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Face: 50x50 -> Width Ratio 0.5 (> 0.45)
        # Position: y=25, h=50. Center = 50. 50/100 = 0.5 (Neutral vertical)
        self.video_sensor.face_cascade.detectMultiScale.return_value = [[25, 25, 50, 50]]

        metrics = self.video_sensor.analyze_frame(frame)

        self.assertIn("face_size_ratio", metrics)
        self.assertAlmostEqual(metrics["face_size_ratio"], 0.5)
        self.assertEqual(metrics["posture_state"], "leaning_forward")

    def test_posture_leaning_back(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Face: 10x10 -> Width Ratio 0.1 (< 0.15)
        self.video_sensor.face_cascade.detectMultiScale.return_value = [[45, 45, 10, 10]]

        metrics = self.video_sensor.analyze_frame(frame)

        self.assertAlmostEqual(metrics["face_size_ratio"], 0.1)
        self.assertEqual(metrics["posture_state"], "leaning_back")

    def test_posture_slouching(self):
        # Face at bottom
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # x=25, y=60, w=50, h=50
        # Center Y = 60 + 25 = 85 -> 0.85 (> 0.65 threshold)
        self.video_sensor.face_cascade.detectMultiScale.return_value = [[25, 60, 50, 50]]

        metrics = self.video_sensor.analyze_frame(frame)

        self.assertIn("vertical_position", metrics)
        self.assertAlmostEqual(metrics["vertical_position"], 0.85)

        # Let's make the face smaller for pure slouching test
        # Size 30 (0.3) -> Neutral size
        # Position 70 -> Center 85 (0.85) -> Slouching
        # FORCE update (bypass eco mode cache)
        self.video_sensor.last_face_check_time = 0
        self.video_sensor.face_cascade.detectMultiScale.return_value = [[35, 70, 30, 30]]
        # Force re-detection
        self.video_sensor.last_face_check_time = 0
        metrics = self.video_sensor.analyze_frame(frame)
        self.assertEqual(metrics["posture_state"], "slouching")

    def test_no_face_detected(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.video_sensor.face_cascade.detectMultiScale.return_value = []

        metrics = self.video_sensor.analyze_frame(frame)

        self.assertFalse(metrics["face_detected"])
        self.assertEqual(metrics["face_count"], 0)
        # These keys should exist but be 0.0, because analyze_frame always populates them
        self.assertEqual(metrics["face_size_ratio"], 0.0)
        self.assertEqual(metrics["vertical_position"], 0.0)
        self.assertEqual(metrics["horizontal_position"], 0.0)

if __name__ == '__main__':
    unittest.main()
