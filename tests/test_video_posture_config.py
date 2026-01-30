import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sensors.video_sensor import VideoSensor

class TestVideoPostureConfig(unittest.TestCase):
    def setUp(self):
        self.sensor = VideoSensor(camera_index=None)
        # Mock dependencies
        self.sensor.logger = MagicMock()

    @patch('sensors.video_sensor.config')
    def test_posture_without_baseline(self, mock_config):
        # Ensure config.BASELINE_POSTURE is empty
        mock_config.BASELINE_POSTURE = {}

        # 1. Neutral (Middle values)
        metrics = {
            "face_detected": True,
            "face_roll_angle": 0,
            "face_size_ratio": 0.3,
            "vertical_position": 0.3
        }
        self.sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "neutral")

        # 2. Slouching (Hardcoded > 0.65)
        metrics = {
            "face_detected": True,
            "face_roll_angle": 0,
            "face_size_ratio": 0.3,
            "vertical_position": 0.7
        }
        self.sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "slouching")

    @patch('sensors.video_sensor.config')
    def test_posture_with_baseline(self, mock_config):
        # Set a baseline
        baseline = {
            "face_roll_angle": 0,
            "face_size_ratio": 0.2, # Smaller face naturally
            "vertical_position": 0.4 # Sits lower naturally
        }
        mock_config.BASELINE_POSTURE = baseline

        # 1. Neutral (Matches baseline)
        metrics = {
            "face_detected": True,
            "face_roll_angle": 0,
            "face_size_ratio": 0.2,
            "vertical_position": 0.4
        }
        self.sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "neutral")

        # 2. Leaning Forward (Ratio > 1.3 of baseline)
        # Baseline 0.2. Threshold > 0.26.
        metrics = {
            "face_detected": True,
            "face_roll_angle": 0,
            "face_size_ratio": 0.27,
            "vertical_position": 0.4
        }
        self.sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "leaning_forward")

        # 3. Slouching (Delta > 0.15)
        # Baseline 0.4. Threshold > 0.55.
        metrics = {
            "face_detected": True,
            "face_roll_angle": 0,
            "face_size_ratio": 0.2,
            "vertical_position": 0.56
        }
        self.sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "slouching")

        # 4. Tilt (Delta > 20)
        metrics = {
            "face_detected": True,
            "face_roll_angle": 25, # +25 deg
            "face_size_ratio": 0.2,
            "vertical_position": 0.4
        }
        self.sensor._calculate_posture(metrics)
        self.assertEqual(metrics["posture_state"], "tilted_right")

if __name__ == '__main__':
    unittest.main()
