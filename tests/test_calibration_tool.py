import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import json
import shutil
import tempfile

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module to be tested
from tools import calibrate

class TestCalibrationEngine(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for user data
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'config.json')

        # Patch USER_DATA_DIR in config (assuming calibrate uses it via config or attribute)
        # calibrate.py: self.user_data_dir = getattr(config, 'USER_DATA_DIR', 'user_data')
        # So we need to patch config before creating CalibrationEngine OR patch the instance attribute

        self.patcher_config = patch('tools.calibrate.config.USER_DATA_DIR', self.test_dir)
        self.mock_user_data_dir = self.patcher_config.start()

    def tearDown(self):
        self.patcher_config.stop()
        shutil.rmtree(self.test_dir)

    @patch('tools.calibrate.AudioSensor')
    @patch('tools.calibrate.VideoSensor')
    def test_calibration_flow(self, MockVideoSensor, MockAudioSensor):
        # Setup Mocks
        mock_audio = MockAudioSensor.return_value
        mock_video = MockVideoSensor.return_value

        # Mock Audio Data (RMS)
        # Provide enough chunks for the loop (10s @ 0.1s sleep = ~100 calls)
        # We'll just make it return a constant or cycle
        mock_audio.get_chunk.return_value = (b'somebytes', None)
        mock_audio.analyze_chunk.return_value = {'rms': 0.1}

        # Mock Video Data (Activity & Posture)
        mock_video.get_frame.return_value = ('someframe', None)
        mock_video.process_frame.return_value = {
            'video_activity': 10.0,
            'face_detected': True,
            'face_roll_angle': 5.0,
            'face_size_ratio': 0.5,
            'vertical_position': 100,
            'horizontal_position': 200
        }

        # Instantiate Engine
        engine = calibrate.CalibrationEngine()

        # Verify it's using our temp dir
        self.assertEqual(engine.user_data_dir, self.test_dir)

        # 1. Test Audio Silence Calibration
        # Mock time.sleep to speed up
        with patch('time.sleep', return_value=None):
            # Also mock print to avoid clutter
            with patch('builtins.print'):
                threshold = engine.calibrate_audio_silence(duration=1) # 1 sec for speed

        # Expectation: RMS is 0.1. Mean=0.1, Std=0. Max=0.1.
        # Threshold = max(0.1 + 0, 0.1 * 1.2) = 0.12
        self.assertAlmostEqual(threshold, 0.12, places=2)

        # 2. Test Activity Thresholds
        with patch('time.sleep', return_value=None):
            with patch('builtins.print'):
                results = engine.calibrate_activity_thresholds(duration=1)

        # Audio RMS 0.1 -> Threshold 0.12
        self.assertAlmostEqual(results['AUDIO_THRESHOLD_HIGH'], 0.12, places=2)

        # Video Activity 10.0 -> Mean=10, Max=10, Std=0
        # Threshold = max(10, 10*1.5, 5.0) = 15.0
        self.assertAlmostEqual(results['VIDEO_ACTIVITY_THRESHOLD_HIGH'], 15.0, places=2)

        # 3. Test Video Posture
        with patch('time.sleep', return_value=None):
            with patch('builtins.print'):
                baseline = engine.calibrate_video_posture(duration=1)

        self.assertEqual(baseline['face_roll_angle'], 5.0)
        self.assertEqual(baseline['vertical_position'], 100)

        # 4. Test Save Config
        new_config = {
            "VAD_SILENCE_THRESHOLD": threshold,
            **results,
            "BASELINE_POSTURE": baseline
        }

        with patch('builtins.print'):
             engine.save_config(new_config)

        # Verify file written
        self.assertTrue(os.path.exists(self.config_path))
        with open(self.config_path, 'r') as f:
            saved_data = json.load(f)

        self.assertIn("VAD_SILENCE_THRESHOLD", saved_data)
        self.assertIn("AUDIO_THRESHOLD_HIGH", saved_data)
        self.assertIn("VIDEO_ACTIVITY_THRESHOLD_HIGH", saved_data)
        self.assertIn("BASELINE_POSTURE", saved_data)

        self.assertEqual(saved_data['VIDEO_ACTIVITY_THRESHOLD_HIGH'], 15.0)

    @patch('builtins.input', side_effect=['y', 'y', 'y', 'y']) # Enter (Start Audio), Enter (Start Activity), Enter (Start Video), y (Save)
    @patch('tools.calibrate.AudioSensor')
    @patch('tools.calibrate.VideoSensor')
    def test_run_full_flow(self, MockVideoSensor, MockAudioSensor, MockInput):
        mock_audio = MockAudioSensor.return_value
        mock_video = MockVideoSensor.return_value

        mock_audio.get_chunk.return_value = (b'bytes', None)
        mock_audio.analyze_chunk.return_value = {'rms': 0.1}

        mock_video.get_frame.return_value = ('frame', None)
        mock_video.process_frame.return_value = {
            'video_activity': 10.0,
            'face_detected': True
        }

        engine = calibrate.CalibrationEngine()

        with patch('time.sleep', return_value=None):
            with patch('builtins.print'):
                engine.run()

        # Verify config saved
        self.assertTrue(os.path.exists(self.config_path))

if __name__ == '__main__':
    unittest.main()
