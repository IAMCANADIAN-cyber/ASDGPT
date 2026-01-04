import os
import json
import sys
import importlib
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import cv2

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import AFTER path fix
import tools.calibrate_sensors as calibrate_tool
import config

class TestCalibrationConfig(unittest.TestCase):
    def setUp(self):
        # Ensure user_data exists
        if not os.path.exists(config.USER_DATA_DIR):
            os.makedirs(config.USER_DATA_DIR)

        # Clean up existing calibration file
        self.calib_file = config.CALIBRATION_FILE
        if os.path.exists(self.calib_file):
            os.remove(self.calib_file)

    def tearDown(self):
        # Clean up
        if os.path.exists(self.calib_file):
            os.remove(self.calib_file)
        # Reload config to restore state
        importlib.reload(config)

    @patch('tools.calibrate_sensors.AudioSensor')
    @patch('tools.calibrate_sensors.VideoSensor')
    def test_calibration_flow_and_config_load(self, MockVideoSensor, MockAudioSensor):
        # 1. Setup Mock Sensors
        mock_audio = MockAudioSensor.return_value
        mock_audio.has_error.return_value = False
        # Return a chunk with RMS approx 0.5 (so 0.5^2 = 0.25)
        # np.sqrt(np.mean(chunk**2)) = 0.5
        mock_audio.get_chunk.return_value = (np.full(1024, 0.5), None)
        mock_audio.analyze_chunk.return_value = {"rms": 0.5}

        mock_video = MockVideoSensor.return_value
        mock_video.cap.isOpened.return_value = True

        # Return frames that differ by fixed amount
        # Activity = Mean(AbsDiff(F1, F2))
        # Let's say diff is 20.0 everywhere.
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.full((100, 100, 3), 20, dtype=np.uint8)

        # side_effect to toggle between frames
        mock_video.get_frame.side_effect = [frame1, frame2, frame1, frame2, frame1, frame2] * 10

        # 2. Run Calibration (fast)
        print("Running calibration test...")
        # Redirect stdout to suppress progress bar spam
        with patch('sys.stdout', new=open(os.devnull, 'w')):
            calibrate_tool.calibrate(duration=0.5)

        # 3. Verify File Created
        self.assertTrue(os.path.exists(self.calib_file), "Calibration file was not created.")

        with open(self.calib_file, 'r') as f:
            data = json.load(f)

        # Audio: Mean=0.5, Std=0.0. Max=0.5.
        # Rec = Max(0.5 + 0, 0.5*1.2, 0.05) = 0.6
        self.assertIn("AUDIO_THRESHOLD_HIGH", data)
        self.assertAlmostEqual(data["AUDIO_THRESHOLD_HIGH"], 0.6, places=1)

        # Video: Mean=20, Std=0. Max=20.
        # Rec = Max(20+0, 20*1.5, 5.0) = 30.0
        self.assertIn("VIDEO_ACTIVITY_THRESHOLD_HIGH", data)
        self.assertAlmostEqual(data["VIDEO_ACTIVITY_THRESHOLD_HIGH"], 30.0, places=1)

        # 4. Verify Config Load
        print("Reloading config to test loading...")
        importlib.reload(config)

        self.assertEqual(config.AUDIO_THRESHOLD_HIGH, data["AUDIO_THRESHOLD_HIGH"])
        self.assertEqual(config.VIDEO_ACTIVITY_THRESHOLD_HIGH, data["VIDEO_ACTIVITY_THRESHOLD_HIGH"])
        print(f"Config successfully loaded: Audio={config.AUDIO_THRESHOLD_HIGH}, Video={config.VIDEO_ACTIVITY_THRESHOLD_HIGH}")

if __name__ == '__main__':
    unittest.main()
