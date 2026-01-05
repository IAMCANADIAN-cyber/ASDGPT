
import sys
import unittest
import time
import threading
from unittest.mock import MagicMock, patch
import numpy as np
import os

# Mock dependencies before import
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['keyboard'] = MagicMock()

# Now import
import config
from core.logic_engine import LogicEngine
from main import Application

# Hardcode config values to avoid external file dependencies during test
config.LOG_FILE = "test_crash.log"
config.LOG_LEVEL = "DEBUG"

class TestCrash(unittest.TestCase):
    def test_rapid_start_stop(self):
        """
        Simulates rapid start and stop cycles to detect race conditions and zombie threads.
        """
        print("\n--- Starting Rapid Start/Stop Stress Test ---")

        cycles = 5 # Number of start/stop cycles

        for i in range(cycles):
            print(f"Cycle {i+1}/{cycles}")

            # Setup specific mocks for this cycle
            with patch('main.AudioSensor') as MockAudioClass, patch('main.VideoSensor') as MockVideoClass:

                # Mock VideoSensor instance
                mock_video_instance = MockVideoClass.return_value
                # Mock get_frame to return a valid tuple (frame, error)
                # Frame should be a valid numpy array or None
                dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
                mock_video_instance.get_frame.return_value = (dummy_frame, None)
                mock_video_instance.has_error.return_value = False

                # Mock AudioSensor instance
                mock_audio_instance = MockAudioClass.return_value
                # Mock get_chunk to return (chunk, error)
                dummy_chunk = np.zeros(1024, dtype=np.float32)
                mock_audio_instance.get_chunk.return_value = (dummy_chunk, None)
                mock_audio_instance.has_error.return_value = False

                # Instantiate Application
                app = Application()

                # Run briefly
                # Start threads
                app.video_thread = threading.Thread(target=app._video_worker, daemon=True)
                app.video_thread.start()
                app.audio_thread = threading.Thread(target=app._audio_worker, daemon=True)
                app.audio_thread.start()

                time.sleep(0.5) # Let it run for a bit

                # Shutdown
                app.quit_application()
                app._shutdown()

                # Verify threads are dead
                if app.video_thread and app.video_thread.is_alive():
                    self.fail(f"Video thread failed to join in cycle {i+1}")
                if app.audio_thread and app.audio_thread.is_alive():
                    self.fail(f"Audio thread failed to join in cycle {i+1}")

                # Verify LogicEngine threads (LMM)
                if app.logic_engine.lmm_thread and app.logic_engine.lmm_thread.is_alive():
                    self.fail(f"LMM thread failed to join in cycle {i+1}")

        print("--- Stress Test Passed: No Zombie Threads Detected ---")

if __name__ == '__main__':
    unittest.main()
