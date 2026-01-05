import sys
import unittest
import threading
import time
import numpy as np
from unittest.mock import MagicMock

# --- Mocks ---
# We need to mock these BEFORE importing main/sensors

# Mock sounddevice
mock_sd = MagicMock()
sys.modules['sounddevice'] = mock_sd

# Mock cv2
mock_cv2 = MagicMock()
sys.modules['cv2'] = mock_cv2

# Mock other deps to avoid import errors
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['keyboard'] = MagicMock() # Mock keyboard as it requires root/display

# Define behavior for the mocks

# Audio Stream Mock
class MockStream:
    def __init__(self, *args, **kwargs):
        self.active = True
        self.closed = False
        self._stop_event = threading.Event()

    def start(self):
        self.active = True

    def read(self, size):
        # Simulate blocking read
        # We wait until stopped or timeout.
        # If the shutdown logic is correct (release called first),
        # self.active will be False quickly, breaking this loop.

        start_t = time.time()
        while self.active:
            time.sleep(0.1)
            # Simulate a "hang" if we never get stopped
            if time.time() - start_t > 3:
                # Just return to avoid test freeze, but this indicates a hang
                # relative to the 2s shutdown requirement.
                break

        # Return dummy data
        return (np.zeros((size, 1), dtype=np.float32), False)

    def stop(self):
        self.active = False
        self._stop_event.set()

    def close(self):
        self.closed = True
        self.active = False

mock_sd.InputStream.side_effect = MockStream
mock_sd.query_devices.return_value = [{'name': 'Mock Device'}]
mock_sd.PortAudioError = Exception # Mock exception

# Video Capture Mock
class MockVideoCapture:
    def __init__(self, *args, **kwargs):
        self.opened = True

    def isOpened(self):
        return self.opened

    def read(self):
        # Simulate blocking read
        start_t = time.time()
        while self.opened:
            time.sleep(0.1)
            if time.time() - start_t > 3:
                break
        return (True, np.zeros((480, 640, 3), dtype=np.uint8))

    def release(self):
        self.opened = False

mock_cv2.VideoCapture.side_effect = MockVideoCapture
mock_cv2.data.haarcascades = "/tmp/"
mock_cv2.CascadeClassifier.return_value.empty.return_value = False # Face detector "loaded"
mock_cv2.cvtColor.return_value = np.zeros((480, 640), dtype=np.uint8)
mock_cv2.resize.return_value = np.zeros((100, 100), dtype=np.uint8)
mock_cv2.absdiff.return_value = np.zeros((100, 100), dtype=np.uint8)
mock_cv2.COLOR_BGR2GRAY = 6

# Now import the app
# We need to ensure config is clean or mocked
import config
config.LOG_FILE = "test_crash.log"
config.CAMERA_INDEX = 0
config.LOG_LEVEL = "INFO"

from main import Application

class TestShutdownHang(unittest.TestCase):
    def test_shutdown_performance(self):
        print("\n--- Starting Shutdown Hang Test ---")

        app = Application()

        # Start app in a thread (simulate main execution)
        # We don't call app.run() because it has a loop.
        # We start the worker threads manually or just call run and run it in a thread.
        # calling app.run() is better integration test.

        app_thread = threading.Thread(target=app.run)
        app_thread.start()

        # Let it "run" for a second to ensure workers are in their loops
        print("App running...")
        time.sleep(1.0)

        # Trigger shutdown
        print("Triggering shutdown...")
        start_time = time.time()
        app.quit_application()

        # Wait for thread to join (This corresponds to the main loop exiting)
        # The main loop calls _shutdown, which joins the workers.
        # If workers hang, _shutdown hangs, and app.run() hangs.
        app_thread.join(timeout=5)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Shutdown took {duration:.2f} seconds")

        # Cleanup if needed (force threads to stop if they are still running to avoid mess)
        app.running = False
        if hasattr(app, 'video_sensor'): app.video_sensor.release()
        if hasattr(app, 'audio_sensor'): app.audio_sensor.release()

        # Verify
        if app_thread.is_alive():
            print("FAILURE: App thread is still alive (Hang detected)")
            self.fail("Application hung during shutdown (thread still alive)")

        if duration > 2.0:
            print(f"FAILURE: Shutdown took too long ({duration:.2f}s > 2.0s)")
            self.fail(f"Shutdown too slow: {duration:.2f}s")

        print("SUCCESS: Shutdown completed cleanly.")

if __name__ == '__main__':
    unittest.main()
