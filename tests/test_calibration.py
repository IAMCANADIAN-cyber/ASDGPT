import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import json

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.calibrate import CalibrationEngine

class TestCalibrationEngine(unittest.TestCase):
    def setUp(self):
        # Patch dependencies
        self.patchers = []

        self.mock_audio_cls = MagicMock()
        self.mock_video_cls = MagicMock()
        self.mock_input = MagicMock()
        self.mock_print = MagicMock()

        self.patchers.append(patch('tools.calibrate.AudioSensor', self.mock_audio_cls))
        self.patchers.append(patch('tools.calibrate.VideoSensor', self.mock_video_cls))
        self.patchers.append(patch('builtins.input', self.mock_input))
        self.patchers.append(patch('builtins.print', self.mock_print))
        self.patchers.append(patch('time.sleep', MagicMock())) # Skip sleep
        self.patchers.append(patch('os.makedirs', MagicMock())) # Prevent dir creation

        # Start patches
        for patcher in self.patchers:
            patcher.start()

        self.mock_audio_instance = self.mock_audio_cls.return_value
        self.mock_video_instance = self.mock_video_cls.return_value

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()

    def test_calibrate_audio_silence_delegation(self):
        engine = CalibrationEngine()

        # Setup mock return
        self.mock_audio_instance.calibrate.return_value = 0.05

        # Run
        threshold = engine.calibrate_audio_silence(duration=10)

        # Assert
        self.mock_audio_instance.calibrate.assert_called_once()
        args, kwargs = self.mock_audio_instance.calibrate.call_args
        self.assertEqual(kwargs['duration'], 10.0)
        self.assertEqual(threshold, 0.05)

    def test_calibrate_video_posture_delegation(self):
        engine = CalibrationEngine()

        # Setup mock return
        expected_baseline = {"face_roll_angle": 5.0}
        self.mock_video_instance.calibrate.return_value = expected_baseline

        # Run
        baseline = engine.calibrate_video_posture(duration=5)

        # Assert
        self.mock_video_instance.calibrate.assert_called_once()
        args, kwargs = self.mock_video_instance.calibrate.call_args
        self.assertEqual(kwargs['duration'], 5.0)
        self.assertEqual(baseline, expected_baseline)

    def test_save_config(self):
        engine = CalibrationEngine()
        new_config = {"TEST_KEY": "TEST_VAL"}

        # Mock loading existing config
        with patch("builtins.open", mock_open(read_data='{"EXISTING": "VAL"}')) as mock_file:
            with patch("os.path.exists", return_value=True):
                with patch("json.dump") as mock_json_dump:
                    engine.save_config(new_config)

                    # Check that json.dump was called with updated config
                    args, _ = mock_json_dump.call_args
                    saved_dict = args[0]
                    self.assertEqual(saved_dict["EXISTING"], "VAL")
                    self.assertEqual(saved_dict["TEST_KEY"], "TEST_VAL")

    def test_full_run_flow_save_yes(self):
        engine = CalibrationEngine()

        # Mock methods to return immediately
        engine.calibrate_audio_silence = MagicMock(return_value=0.05)
        engine.calibrate_video_posture = MagicMock(return_value={"posture": "neutral"})
        engine.save_config = MagicMock()

        # Mock user input:
        # 1. Start Audio (Enter)
        # 2. Start Video (Enter)
        # 3. Save Config (y)
        self.mock_input.side_effect = ["", "", "y"]

        engine.run()

        engine.calibrate_audio_silence.assert_called_once()
        engine.calibrate_video_posture.assert_called_once()
        engine.save_config.assert_called_once()

        # Check argument to save_config
        expected_config_update = {
            "VAD_SILENCE_THRESHOLD": 0.05,
            "BASELINE_POSTURE": {"posture": "neutral"}
        }
        engine.save_config.assert_called_with(expected_config_update)

    def test_full_run_flow_save_no(self):
        engine = CalibrationEngine()

        engine.calibrate_audio_silence = MagicMock(return_value=0.05)
        engine.calibrate_video_posture = MagicMock(return_value={})
        engine.save_config = MagicMock()

        self.mock_input.side_effect = ["", "", "n"]

        engine.run()

        engine.save_config.assert_not_called()

    def test_keyboard_interrupt_audio(self):
        engine = CalibrationEngine()

        # Simulate KeyboardInterrupt in sensor
        self.mock_audio_instance.calibrate.side_effect = KeyboardInterrupt

        threshold = engine.calibrate_audio_silence()

        # Should catch and return default (0.01)
        # Note: We can't rely on config default being exactly 0.01 if config is real,
        # but the tool hardcodes fallback return value as getattr(config, 'VAD_SILENCE_THRESHOLD', 0.01)
        self.assertIsInstance(threshold, float)

if __name__ == '__main__':
    unittest.main()
