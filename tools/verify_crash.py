
import sys
import time
import threading
import unittest
from unittest.mock import MagicMock

# Mock dependencies before import
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['keyboard'] = MagicMock()

# Now import
from main import Application
import config

class TestShutdown(unittest.TestCase):
    def test_shutdown_cycle(self):
        """Simulates rapid start/stop cycles to verify thread cleanup."""
        # Use a dummy log file
        config.LOG_FILE = "test_shutdown.log"
        config.CAMERA_INDEX = None # Prevent actual camera access attempts in mock env

        for i in range(5):
            print(f"Cycle {i+1} starting...")
            app = Application()

            # Start threads manually as we are not calling app.run() which loops
            app.video_thread = threading.Thread(target=app._video_worker, daemon=True)
            app.video_thread.start()
            app.audio_thread = threading.Thread(target=app._audio_worker, daemon=True)
            app.audio_thread.start()

            # Let it run briefly
            time.sleep(0.5)

            # Initiate shutdown
            app.running = False
            app._shutdown()

            # Verify threads are dead
            if app.video_thread:
                self.assertFalse(app.video_thread.is_alive(), f"Video thread still alive in cycle {i+1}")
            if app.audio_thread:
                self.assertFalse(app.audio_thread.is_alive(), f"Audio thread still alive in cycle {i+1}")

            print(f"Cycle {i+1} complete. Threads joined.")

if __name__ == '__main__':
    unittest.main()
