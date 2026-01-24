import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from sensors.video_sensor import VideoSensor

class TestVideoSensorCalibration(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.logger = MagicMock()
        # Mock CascadeClassifier to avoid file loading issues and speed up tests
        with patch('cv2.CascadeClassifier') as MockCascade:
             self.video_sensor = VideoSensor(camera_index=None, data_logger=self.logger)
             self.video_sensor.face_cascade = MockCascade.return_value
             self.video_sensor.eye_cascade = MockCascade.return_value

    @patch('sensors.video_sensor.config.BASELINE_POSTURE', {})
    def test_fallback_logic(self):
        """Verify fallback to hardcoded thresholds when baseline is empty."""
        metrics = {
            "face_detected": True,
            "face_roll_angle": 0,
            "face_size_ratio": 0.5, # > 0.45 (Leaning Forward hardcoded)
            "vertical_position": 0.4
        }
        self.video_sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "leaning_forward")

        metrics["face_size_ratio"] = 0.1 # < 0.15 (Leaning Back hardcoded)
        self.video_sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "leaning_back")

    @patch('sensors.video_sensor.config.BASELINE_POSTURE', {
        "face_size_ratio": 0.3,
        "vertical_position": 0.5,
        "face_roll_angle": 0
    })
    def test_calibrated_logic(self):
        """Verify relative thresholds when baseline is present."""
        # Baseline size is 0.3.
        # Leaning Forward: > 1.3 * 0.3 = 0.39.
        # Leaning Back: < 0.7 * 0.3 = 0.21.

        metrics = {
            "face_detected": True,
            "face_roll_angle": 0,
            "face_size_ratio": 0.4, # 0.4 / 0.3 = 1.33 > 1.3 -> Leaning Forward
            "vertical_position": 0.5
        }
        self.video_sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "leaning_forward")

        metrics["face_size_ratio"] = 0.2 # 0.2 / 0.3 = 0.66 < 0.7 -> Leaning Back
        self.video_sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "leaning_back")

        metrics["face_size_ratio"] = 0.3 # Neutral size
        # Slouching: vertical - baseline > 0.15. Baseline vertical is 0.5.
        # So vertical > 0.65 is slouching.
        metrics["vertical_position"] = 0.7 # 0.7 - 0.5 = 0.2 > 0.15 -> Slouching
        self.video_sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "slouching")

        metrics["vertical_position"] = 0.5 # Neutral
        self.video_sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "neutral")

    @patch('sensors.video_sensor.config.BASELINE_POSTURE', {
        "face_size_ratio": 0.3,
        "vertical_position": 0.5,
        "face_roll_angle": 0
    })
    def test_tilt_absolute_with_calibration(self):
        """Verify tilt is still absolute even with calibration."""
        metrics = {
            "face_detected": True,
            "face_roll_angle": 25, # > 20 -> Tilted Right
            "face_size_ratio": 0.3,
            "vertical_position": 0.5
        }
        self.video_sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "tilted_right")

if __name__ == '__main__':
    unittest.main()
