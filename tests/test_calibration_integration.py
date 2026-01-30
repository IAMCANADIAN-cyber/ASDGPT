import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock cv2 before importing VideoSensor
sys.modules['cv2'] = MagicMock()

from sensors.video_sensor import VideoSensor
import config

class TestCalibrationIntegration(unittest.TestCase):
    def setUp(self):
        # Prevent actual camera init
        self.sensor = VideoSensor(camera_index=None)

    def test_default_heuristics(self):
        """Verify fallback to hardcoded thresholds when no baseline exists."""
        with patch('sensors.video_sensor.config.BASELINE_POSTURE', {}):
            # 1. Slouching (Default threshold > 0.65)
            metrics = {
                "face_detected": True,
                "vertical_position": 0.7,
                "face_size_ratio": 0.3,
                "face_roll_angle": 0
            }
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "slouching")

            # 2. Neutral (0.5 is < 0.65)
            metrics["vertical_position"] = 0.5
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "neutral")

    def test_calibrated_heuristics_slouch(self):
        """Verify logic uses baseline for slouching."""
        # Baseline y=0.4. Threshold is +0.15 -> 0.55.
        baseline = {"vertical_position": 0.4, "face_size_ratio": 0.3, "face_roll_angle": 0}

        with patch('sensors.video_sensor.config.BASELINE_POSTURE', baseline):
            # 1. Neutral (0.5 < 0.55)
            metrics = {
                "face_detected": True,
                "vertical_position": 0.5,
                "face_size_ratio": 0.3,
                "face_roll_angle": 0
            }
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "neutral")

            # 2. Slouching (0.6 > 0.55)
            metrics["vertical_position"] = 0.6
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "slouching")

    def test_calibrated_heuristics_leaning_forward(self):
        """Verify logic uses baseline for leaning forward."""
        # Baseline size=0.2. Threshold 1.5x -> 0.3.
        baseline = {"vertical_position": 0.4, "face_size_ratio": 0.2, "face_roll_angle": 0}

        with patch('sensors.video_sensor.config.BASELINE_POSTURE', baseline):
            # 1. Neutral (0.25 < 0.3)
            metrics = {
                "face_detected": True,
                "vertical_position": 0.4,
                "face_size_ratio": 0.25,
                "face_roll_angle": 0
            }
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "neutral")

            # 2. Leaning Forward (0.35 > 0.3)
            metrics["face_size_ratio"] = 0.35
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "leaning_forward")

    def test_calibrated_heuristics_tilt(self):
        """Verify logic uses baseline for tilt."""
        # Baseline tilt=10 (User naturally tilts right). Threshold +/- 20 -> -10 to 30.
        baseline = {"vertical_position": 0.4, "face_size_ratio": 0.3, "face_roll_angle": 10}

        with patch('sensors.video_sensor.config.BASELINE_POSTURE', baseline):
            # 1. Neutral (Tilt 20 is within 10+20 range)
            # Diff = 20 - 10 = 10. abs(10) < 20.
            metrics = {
                "face_detected": True,
                "vertical_position": 0.4,
                "face_size_ratio": 0.3,
                "face_roll_angle": 20
            }
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "neutral")

            # 2. Tilted Right (Tilt 35. Diff 25 > 20)
            metrics["face_roll_angle"] = 35
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "tilted_right")

            # 3. Tilted Left (Tilt -15. Diff -25. abs > 20)
            metrics["face_roll_angle"] = -15
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "tilted_left")

if __name__ == '__main__':
    unittest.main()
