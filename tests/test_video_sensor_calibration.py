import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sensors.video_sensor import VideoSensor
import config

class TestVideoSensorCalibration(unittest.TestCase):
    def setUp(self):
        # We don't need a real camera
        with patch('cv2.VideoCapture') as mock_cap:
             self.sensor = VideoSensor(camera_index=None)

    def test_absolute_thresholds_fallback(self):
        """Test that sensor falls back to absolute thresholds when no baseline exists."""
        # Ensure baseline is empty
        with patch('config.BASELINE_POSTURE', {}):

            # 1. Leaning Forward (Absolute > 0.45)
            metrics = {"face_detected": True, "face_size_ratio": 0.50, "vertical_position": 0.3, "face_roll_angle": 0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "leaning_forward")

            # 2. Neutral (Absolute 0.15 < size < 0.45)
            metrics = {"face_detected": True, "face_size_ratio": 0.30, "vertical_position": 0.3, "face_roll_angle": 0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "neutral")

            # 3. Slouching (Absolute > 0.65)
            metrics = {"face_detected": True, "face_size_ratio": 0.30, "vertical_position": 0.70, "face_roll_angle": 0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "slouching")

    def test_calibrated_leaning(self):
        """Test relative leaning detection using baseline."""
        baseline = {
            "face_size_ratio": 0.20,
            "vertical_position": 0.30,
            "face_roll_angle": 0.0,
            "horizontal_position": 0.5
        }

        with patch('config.BASELINE_POSTURE', baseline):
            # 1. Leaning Forward
            # Input 0.30. Ratio = 0.30 / 0.20 = 1.5 (> 1.3)
            # Note: 0.30 is NOT enough for absolute threshold (0.45)
            metrics = {"face_detected": True, "face_size_ratio": 0.30, "vertical_position": 0.30, "face_roll_angle": 0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "leaning_forward", "Should detect relative lean forward")

            # 2. Leaning Back
            # Input 0.12. Ratio = 0.12 / 0.20 = 0.6 (< 0.7)
            metrics = {"face_detected": True, "face_size_ratio": 0.12, "vertical_position": 0.30, "face_roll_angle": 0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "leaning_back", "Should detect relative lean back")

            # 3. Neutral (Small deviation)
            # Input 0.24. Ratio = 1.2 (< 1.3)
            metrics = {"face_detected": True, "face_size_ratio": 0.24, "vertical_position": 0.30, "face_roll_angle": 0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "neutral")

    def test_calibrated_slouching(self):
        """Test relative slouching detection."""
        baseline = {
            "face_size_ratio": 0.20,
            "vertical_position": 0.30,
            "face_roll_angle": 0.0,
            "horizontal_position": 0.5
        }

        with patch('config.BASELINE_POSTURE', baseline):
            # 1. Slouching
            # Input 0.50. Delta = 0.50 - 0.30 = 0.20 (> 0.15)
            # Note: 0.50 is NOT enough for absolute threshold (0.65)
            metrics = {"face_detected": True, "face_size_ratio": 0.20, "vertical_position": 0.50, "face_roll_angle": 0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "slouching", "Should detect relative slouching")

            # 2. Neutral
            # Input 0.40. Delta = 0.10 (< 0.15)
            metrics = {"face_detected": True, "face_size_ratio": 0.20, "vertical_position": 0.40, "face_roll_angle": 0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "neutral")

    def test_calibrated_tilt(self):
        """Test relative tilt detection."""
        baseline = {
            "face_size_ratio": 0.20,
            "vertical_position": 0.30,
            "face_roll_angle": 5.0, # User naturally tilts slightly right
            "horizontal_position": 0.5
        }

        with patch('config.BASELINE_POSTURE', baseline):
            # 1. Tilted Right (Relative)
            # Input 22. Delta = 22 - 5 = 17 (> 15)
            # Absolute is > 20 anyway, so this one overlaps, but let's try one that doesn't overlap absolute
            # Absolute threshold is > 20.
            # Let's try Input 21. Delta = 16. It triggers both.
            # Let's try natural tilt LEFT (-5)
            # Baseline: -5. Input -22. Delta = |-22 - (-5)| = |-17| = 17 > 15.
            metrics = {"face_detected": True, "face_size_ratio": 0.20, "vertical_position": 0.30, "face_roll_angle": -22.0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "tilted_left")

            # Test slightly more sensitive case
            # Baseline 0. Input 18. Delta 18 > 15. Absolute 20.
            # 18 < 20 (Absolute would be Neutral)
            baseline["face_roll_angle"] = 0.0
            metrics = {"face_detected": True, "face_size_ratio": 0.20, "vertical_position": 0.30, "face_roll_angle": 18.0}
            self.sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "tilted_right", "Should detect 18 deg tilt relative to 0 baseline")


if __name__ == '__main__':
    unittest.main()
