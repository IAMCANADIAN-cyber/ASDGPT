import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import json
import sys
import tempfile
import shutil

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.calibrate import CalibrationEngine

class TestCalibrationTool(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'config.json')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('tools.calibrate.AudioSensor')
    @patch('tools.calibrate.VideoSensor')
    @patch('tools.calibrate.config')
    def test_init_creates_dir(self, mock_config, mock_video_cls, mock_audio_cls):
        mock_config.USER_DATA_DIR = self.test_dir
        engine = CalibrationEngine()
        self.assertTrue(os.path.exists(self.test_dir))
        self.assertEqual(engine.config_path, self.config_path)

    @patch('tools.calibrate.AudioSensor')
    @patch('tools.calibrate.VideoSensor')
    @patch('tools.calibrate.config')
    def test_save_load_config(self, mock_config, mock_video_cls, mock_audio_cls):
        mock_config.USER_DATA_DIR = self.test_dir
        engine = CalibrationEngine()

        # Test Save
        new_conf = {"TEST_KEY": 123}
        engine.save_config(new_conf)

        self.assertTrue(os.path.exists(self.config_path))
        with open(self.config_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["TEST_KEY"], 123)

        # Test Load
        loaded = engine.load_current_config()
        self.assertEqual(loaded["TEST_KEY"], 123)

        # Test Update (not overwrite)
        engine.save_config({"OTHER_KEY": 456})
        loaded = engine.load_current_config()
        self.assertEqual(loaded["TEST_KEY"], 123)
        self.assertEqual(loaded["OTHER_KEY"], 456)

    @patch('tools.calibrate.AudioSensor')
    @patch('tools.calibrate.VideoSensor')
    @patch('tools.calibrate.config')
    @patch('builtins.input')
    @patch('time.sleep') # Skip sleeps
    def test_run_full_flow(self, mock_sleep, mock_input, mock_config, mock_video_cls, mock_audio_cls):
        mock_config.USER_DATA_DIR = self.test_dir

        # Setup mocks
        mock_audio = mock_audio_cls.return_value
        mock_audio.calibrate.return_value = 0.05

        mock_video = mock_video_cls.return_value
        mock_video.calibrate.return_value = {"face_roll_angle": 5.0}

        # Inputs:
        # 1. Start Audio (Enter)
        # 2. Start Video (Enter)
        # 3. Save? (y)
        mock_input.side_effect = ["", "", "y"]

        engine = CalibrationEngine()
        engine.run()

        # Verify calls
        mock_audio.calibrate.assert_called_once()
        mock_video.calibrate.assert_called_once()

        # Verify file saved
        with open(self.config_path, 'r') as f:
            data = json.load(f)

        self.assertEqual(data["VAD_SILENCE_THRESHOLD"], 0.05)
        self.assertEqual(data["BASELINE_POSTURE"]["face_roll_angle"], 5.0)

    @patch('tools.calibrate.AudioSensor')
    @patch('tools.calibrate.VideoSensor')
    @patch('tools.calibrate.config')
    @patch('builtins.input')
    def test_run_discard_changes(self, mock_input, mock_config, mock_video_cls, mock_audio_cls):
        mock_config.USER_DATA_DIR = self.test_dir

        # Setup mocks returning valid data
        mock_audio_cls.return_value.calibrate.return_value = 0.05
        mock_video_cls.return_value.calibrate.return_value = {"face_roll_angle": 5.0}

        # Inputs: Enter, Enter, 'n' (discard)
        mock_input.side_effect = ["", "", "n"]

        engine = CalibrationEngine()
        engine.run()

        # Verify file NOT saved
        self.assertFalse(os.path.exists(self.config_path))

if __name__ == '__main__':
    unittest.main()
