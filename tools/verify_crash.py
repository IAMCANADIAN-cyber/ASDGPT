
import sys
import unittest
import time
import threading
from unittest.mock import MagicMock, patch

# Mock dependencies before import
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['cv2'] = MagicMock()

# Now import
from core.logic_engine import LogicEngine
from main import Application
import config

class TestCrash(unittest.TestCase):
    def setUp(self):
        # Prevent actual logging to file during this stress test
        config.LOG_FILE = "test_stress.log"

    def test_rapid_start_stop(self):
        """Simulate rapid start/stop cycles to catch race conditions and hang on exit."""
        print("\nStarting rapid start/stop stress test...")

        for i in range(5):
            print(f"Cycle {i+1}/5")
            app = Application()

            # Start a thread to run the app
            app_thread = threading.Thread(target=app.run)
            app_thread.start()

            # Let it run for a brief moment
            time.sleep(1.0)

            # Request shutdown
            app.quit_application()

            # Wait for thread to join
            start_join = time.time()
            app_thread.join(timeout=3.0)
            end_join = time.time()

            if app_thread.is_alive():
                print(f"Cycle {i+1} FAILED: App thread did not join within 3 seconds.")
                # Forcefully try to stop threads if we can (though in real life this is the hang)
                self.fail("Application failed to shut down cleanly.")
            else:
                print(f"Cycle {i+1} PASSED: Shutdown took {end_join - start_join:.2f}s")

            # Clean up mocks/resources if needed between runs
            # (Application __init__ creates new instances so mostly fine)

if __name__ == '__main__':
    unittest.main()
