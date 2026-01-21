import unittest
from unittest.mock import MagicMock, patch, mock_open
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
        self.mock_json_dump = MagicMock()

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

        # Simulate audio chunks with increasing RMS
        # chunk 1: rms 0.01
        # chunk 2: rms 0.02
        # chunk 3: rms 0.01

        def mock_get_chunk():
            return np.array([0]), None # dummy data

        def mock_analyze_chunk(chunk):
             # Cycle through RMS values
             if not hasattr(mock_analyze_chunk, 'counter'):
                 mock_analyze_chunk.counter = 0
             rms_values = [0.01, 0.02, 0.01]
             val = rms_values[mock_analyze_chunk.counter % len(rms_values)]
             mock_analyze_chunk.counter += 1
             return {"rms": val}

        self.mock_audio.get_chunk.side_effect = mock_get_chunk
        self.mock_audio.analyze_chunk.side_effect = mock_analyze_chunk

        # Run calibration (short duration is mocked via sleep patch, loop runs a few times)
        # We need to control the loop. The loop condition is time.time().
        # Patch time.time to increment
        # start_time, loop1, loop2, loop3, end
        with patch('time.time', side_effect=[0, 0, 1, 2, 11]):
             threshold = engine.calibrate_audio_silence(duration=10)

        # Expected: Mean ~0.0133, Max 0.02, StdDev ~0.0057
        # Threshold logic: Max(Mean + 3*Std, Max*1.2)
        # 0.0133 + 0.017 = 0.03
        # 0.02 * 1.2 = 0.024
        # Expected ~0.03

        self.assertTrue(0.02 < threshold < 0.04)

    def test_calibrate_video_posture(self):
        engine = CalibrationEngine()

        # Simulate video frames
        def mock_get_frame():
            return np.array([0]), None

        def mock_process_frame(frame):
             return {
                 "face_detected": True,
                 "face_roll_angle": 5.0,
                 "face_size_ratio": 0.2,
                 "vertical_position": 0.4,
                 "horizontal_position": 0.5
             }

        self.mock_video.get_frame.side_effect = mock_get_frame
        self.mock_video.process_frame.side_effect = mock_process_frame

        # start, loop1, loop2, end
        with patch('time.time', side_effect=[0, 0, 1, 6]):
             baseline = engine.calibrate_video_posture(duration=5)

        self.assertEqual(baseline["face_roll_angle"], 5.0)
        self.assertEqual(baseline["face_size_ratio"], 0.2)

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
