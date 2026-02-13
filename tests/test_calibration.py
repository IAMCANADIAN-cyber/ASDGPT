import unittest
from unittest.mock import MagicMock, patch, mock_open, ANY
import sys
import os
import json
import numpy as np

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.calibrate import CalibrationEngine

class TestCalibration(unittest.TestCase):
    def setUp(self):
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_input = MagicMock()
        self.mock_print = MagicMock()

        # Patch dependencies
        self.patchers = []

        self.patchers.append(patch('tools.calibrate.AudioSensor', return_value=self.mock_audio))
        self.patchers.append(patch('tools.calibrate.VideoSensor', return_value=self.mock_video))
        self.patchers.append(patch('builtins.input', self.mock_input))
        self.patchers.append(patch('builtins.print', self.mock_print))
        self.patchers.append(patch('time.sleep', MagicMock())) # Skip sleep
        self.patchers.append(patch('os.makedirs', MagicMock())) # Prevent dir creation

        # Start patches
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()

    def test_calibrate_audio_silence(self):
        engine = CalibrationEngine()

        # Mock the sensor's calibrate method to return a known float
        self.mock_audio.calibrate.return_value = 0.03

        # Run calibration
        threshold = engine.calibrate_audio_silence(duration=10)

        # Verify delegation (allowing for extra args like progress_callback and type conversion)
        self.mock_audio.calibrate.assert_called()
        args, kwargs = self.mock_audio.calibrate.call_args
        # Verify duration is passed (might be float)
        self.assertIn('duration', kwargs)
        self.assertEqual(float(kwargs['duration']), 10.0)
        self.assertEqual(threshold, 0.03)

    def test_calibrate_video_posture(self):
        engine = CalibrationEngine()

        # Mock the sensor's calibrate method to return a known dict
        expected_baseline = {"face_roll_angle": 5.0, "face_size_ratio": 0.2}
        self.mock_video.calibrate.return_value = expected_baseline

        # Run calibration
        baseline = engine.calibrate_video_posture(duration=5)

        # Verify delegation
        self.mock_video.calibrate.assert_called()
        args, kwargs = self.mock_video.calibrate.call_args
        self.assertIn('duration', kwargs)
        self.assertEqual(float(kwargs['duration']), 5.0)
        self.assertEqual(baseline, expected_baseline)

    def test_save_config(self):
        engine = CalibrationEngine()
        new_config = {"TEST_KEY": "TEST_VAL"}

        with patch("builtins.open", mock_open(read_data='{"EXISTING": "VAL"}')) as mock_file:
            with patch("os.path.exists", return_value=True):
                with patch("json.dump") as mock_json_dump:
                    engine.save_config(new_config)

                    # Check that json.dump was called with updated config
                    args, _ = mock_json_dump.call_args
                    saved_dict = args[0]
                    self.assertEqual(saved_dict["EXISTING"], "VAL")
                    self.assertEqual(saved_dict["TEST_KEY"], "TEST_VAL")

    def test_full_run_flow(self):
        engine = CalibrationEngine()

        # Mock methods to return immediately
        engine.calibrate_audio_silence = MagicMock(return_value=0.05)
        engine.calibrate_video_posture = MagicMock(return_value={"posture": "neutral"})
        engine.save_config = MagicMock()

        # Mock user input to 'y' for save
        self.mock_input.side_effect = ["", "", "y"]

        engine.run()

        engine.save_config.assert_called()

if __name__ == '__main__':
    unittest.main()
