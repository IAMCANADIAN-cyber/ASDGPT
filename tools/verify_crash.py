
import sys
import unittest
import time
import threading
from unittest.mock import MagicMock

# Mock dependencies before import
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['keyboard'] = MagicMock()

# Configure mocks to prevent noise
mock_cap = MagicMock()
mock_cap.isOpened.return_value = True
mock_cap.read.return_value = (True, MagicMock()) # Mock valid frame capture
sys.modules['cv2'].VideoCapture.return_value = mock_cap

# Mock sounddevice stream
mock_stream = MagicMock()
mock_stream.closed = False # Explicitly set to False
mock_stream.read.return_value = (MagicMock(), False) # Data, overflow
sys.modules['sounddevice'].InputStream.return_value = mock_stream

# Now import
from core.logic_engine import LogicEngine
from main import Application
import config

# Setup test config
config.LOG_FILE = "test_verify_crash.log"
config.LOG_LEVEL = "DEBUG"
config.CAMERA_INDEX = 0
config.USER_DATA_DIR = "user_data_test"

class TestCrash(unittest.TestCase):
    def test_rapid_start_stop(self):
        """Stress test: Start and stop the application rapidly to detect zombie threads."""
        print("\n--- Starting Rapid Start/Stop Stress Test (10 cycles) ---")

        for i in range(10):
            print(f"Cycle {i+1}/10...")

            # Initialize Application
            app = Application()

            # Start worker threads (mocked sensors)
            app.video_thread = threading.Thread(target=app._video_worker, daemon=True)
            app.audio_thread = threading.Thread(target=app._audio_worker, daemon=True)
            app.video_thread.start()
            app.audio_thread.start()

            # Simulate a brief run
            time.sleep(0.1)

            # Trigger Shutdown
            app.quit_application()
            app._shutdown()

            # Check for zombie threads
            # LogicEngine threads?
            if app.logic_engine.lmm_thread and app.logic_engine.lmm_thread.is_alive():
                self.fail(f"LogicEngine LMM thread still alive in cycle {i+1}")

            # Main worker threads?
            if app.video_thread.is_alive():
                 # Give it a tiny bit more time if needed, but it should be joined
                 app.video_thread.join(timeout=0.1)
                 if app.video_thread.is_alive():
                     self.fail(f"Video worker thread still alive in cycle {i+1}")

            if app.audio_thread.is_alive():
                 app.audio_thread.join(timeout=0.1)
                 if app.audio_thread.is_alive():
                     self.fail(f"Audio worker thread still alive in cycle {i+1}")

        print("--- Stress Test Passed: No zombie threads detected. ---")

if __name__ == '__main__':
    unittest.main()
