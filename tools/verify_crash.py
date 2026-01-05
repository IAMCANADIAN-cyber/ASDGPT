import unittest
import sys
import threading
import time
from unittest.mock import MagicMock, patch
import numpy as np

# --- Mocks must be installed before importing application modules ---
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['cv2'] = MagicMock()

# Mock keyboard if it requires root or isn't present
sys.modules['keyboard'] = MagicMock()

# Import application components
from main import Application
import config

class TestStressShutdown(unittest.TestCase):
    def setUp(self):
        # Configure logging to suppress noise during test
        config.LOG_LEVEL = "ERROR"
        # Prevent actual file logging if possible, or use temp file
        config.LOG_FILE = "stress_test_acr.log"

    @patch('sensors.video_sensor.cv2.absdiff')
    @patch('sensors.video_sensor.cv2.cvtColor')
    @patch('sensors.video_sensor.cv2.resize')
    @patch('sensors.video_sensor.cv2.CascadeClassifier')
    @patch('sensors.video_sensor.cv2.VideoCapture')
    @patch('sensors.audio_sensor.sd.InputStream')
    def test_rapid_start_stop(self, mock_audio_stream, mock_video_capture, mock_cascade_classifier, mock_resize, mock_cvtColor, mock_absdiff):
        """
        Simulate rapid start/stop cycles to detect thread hangs or race conditions.
        """
        cycles = 10
        print(f"\nStarting {cycles} rapid start/stop cycles...")

        # Setup CV2 Mocks
        mock_cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_resize.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_absdiff.return_value = np.zeros((100, 100), dtype=np.uint8)

        # Setup Cascade Classifier Mock to return empty list for detections
        mock_cascade = MagicMock()
        mock_cascade.empty.return_value = False
        mock_cascade.detectMultiScale.return_value = [] # No faces
        mock_cascade_classifier.return_value = mock_cascade

        for i in range(cycles):
            print(f"Cycle {i+1}/{cycles}")

            # Setup mocks for this cycle
            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            # Return a valid numpy array frame
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            mock_cap.read.return_value = (True, frame)
            mock_video_capture.return_value = mock_cap

            mock_stream = MagicMock()
            # Return valid audio chunk
            chunk = np.zeros(1024, dtype=np.float32)
            mock_stream.read.return_value = (chunk, False)
            mock_audio_stream.return_value = mock_stream

            app = Application()

            # Start the app in a separate thread so we can control it
            app_thread = threading.Thread(target=app.run)
            app_thread.start()

            # Let it run for a brief moment
            time.sleep(0.5)

            # Initiate shutdown
            app.quit_application()

            # Wait for thread to join
            app_thread.join(timeout=3)

            if app_thread.is_alive():
                print(f"FAIL: App thread failed to join in Cycle {i+1}")
                self.fail(f"Application failed to shut down cleanly in cycle {i+1}")

            # Verify resources released
            # Note: We can't easily verify the real objects since we mocked them,
            # but we can verify if the mock release methods were called.
            # However, the main point is that join() returned.

            print(f"Cycle {i+1} complete.")

        print("Stress test passed.")

if __name__ == '__main__':
    unittest.main()
