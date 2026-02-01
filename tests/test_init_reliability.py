import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add root directory to sys.path
sys.path.append(os.getcwd())

# Mock dependencies that require system access
sys.modules['sounddevice'] = MagicMock()
sys.modules['keyboard'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()

import main
from main import Application

class TestInitLeak(unittest.TestCase):

    @patch('main.VideoSensor')
    @patch('main.AudioSensor')
    @patch('main.WindowSensor')
    @patch('main.LMMInterface')
    @patch('main.LogicEngine')
    @patch('main.InterventionEngine')
    @patch('main.ACRTrayIcon')
    @patch('main.DataLogger')
    def test_init_leak(self, mock_logger, mock_tray, mock_ie, mock_le, mock_lmm, mock_window, mock_audio, mock_video):
        # Setup VideoSensor mock to simulate successful init and resource holding
        video_instance = MagicMock()
        mock_video.return_value = video_instance

        # Setup AudioSensor to raise exception
        mock_audio.side_effect = RuntimeError("Audio device init failed")

        print("\n--- Starting Reproduction Test ---")
        try:
            app = Application()
        except RuntimeError as e:
            print(f"Caught expected exception: {e}")
        except Exception as e:
            print(f"Caught unexpected exception: {e}")

        # Check if video sensor release was called
        if video_instance.release.called:
            print("VideoSensor.release() WAS called. System is safe.")
        else:
            print("VideoSensor.release() was NOT called. RESOURCE LEAK DETECTED.")

        self.assertTrue(video_instance.release.called, "VideoSensor should be released if Application init fails")

if __name__ == '__main__':
    unittest.main()
