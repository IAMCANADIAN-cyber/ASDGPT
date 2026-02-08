
import unittest
import threading
import time
import sys
import logging
from unittest.mock import MagicMock, patch

# Global Mocks setup before any imports
sys.modules['pystray'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['keyboard'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['scipy'] = MagicMock()
sys.modules['scipy.io'] = MagicMock()
sys.modules['scipy.io.wavfile'] = MagicMock()
sys.modules['pyautogui'] = MagicMock()
sys.modules['mouseinfo'] = MagicMock()

# Now we can import the app code safely
# We need to ensure we can import config, so add root to path
import os
sys.path.append(os.getcwd())

from main import Application
import config

class TestStressShutdown(unittest.TestCase):
    def setUp(self):
        # Configure logging to file to avoid console noise, but allow reading it if needed
        config.LOG_FILE = 'stress_test.log'
        # Reset any global state if possible, though strict process isolation is better.

    def test_rapid_start_stop(self):
        """
        Runs the application start/stop cycle 10 times to detect race conditions and zombies.
        """
        print("\n--- Starting Rapid Start/Stop Stress Test (10 cycles) ---")

        cycles = 10
        success_count = 0

        for i in range(cycles):
            print(f"Cycle {i+1}/{cycles}...", end="", flush=True)

            # Setup fresh mocks for each cycle to track calls
            # We mock the internal blocking functions of sensors

            # Mock Video Capture
            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            # Simulate read delay
            def slow_read():
                time.sleep(0.01)
                return True, MagicMock() # ret, frame
            mock_cap.read.side_effect = slow_read

            # Mock Audio Stream
            mock_stream = MagicMock()
            mock_stream.closed = False
            def slow_audio_read(size):
                time.sleep(0.01)
                return MagicMock(), False # data, overflow
            mock_stream.read.side_effect = slow_audio_read

            with patch('cv2.VideoCapture', return_value=mock_cap), \
                 patch('sounddevice.InputStream', return_value=mock_stream):

                app = Application()

                # Start worker threads manually (mimicking app.run() without the main loop block)
                app.running = True
                app.video_thread = threading.Thread(target=app._video_worker, daemon=True)
                app.audio_thread = threading.Thread(target=app._audio_worker, daemon=True)

                app.video_thread.start()
                app.audio_thread.start()

                # Let it run briefly
                time.sleep(0.2)

                # Trigger a simulated intervention that might block?
                # For now, just test basic sensor loop shutdown.

                # Shutdown
                start_time = time.time()
                app._shutdown()
                duration = time.time() - start_time

                # Verification
                if app.video_thread.is_alive() or app.audio_thread.is_alive():
                    print(f" FAILED: Threads failed to join. Video:{app.video_thread.is_alive()}, Audio:{app.audio_thread.is_alive()}")
                    self.fail(f"Cycle {i+1} failed: Zombie threads detected.")

                if duration > 2.0:
                    print(f" SLOW: Shutdown took {duration:.2f}s")
                else:
                    print(" OK")
                    success_count += 1

                # Verify resources released
                mock_cap.release.assert_called()
                mock_stream.close.assert_called()

        print(f"\nPassed {success_count}/{cycles} cycles.")
        self.assertEqual(success_count, cycles)

    def test_shutdown_during_blocking_intervention(self):
        """
        Simulates shutdown while an intervention is 'speaking' (blocking subprocess).
        """
        print("\n--- Testing Shutdown During Blocking Intervention ---")

        app = Application()

        # Mock subprocess.Popen
        # We simulate a process that waits a long time unless terminated

        blocking_event = threading.Event()
        terminate_event = threading.Event()

        mock_process = MagicMock()

        def fake_wait(timeout=None):
            blocking_event.set()
            # Simulate blocking process
            count = 0
            while count < 50: # 5 seconds
                if terminate_event.is_set():
                    # Terminated!
                    return
                time.sleep(0.1)
                count += 1
            # Finished naturally (should not happen if terminated)

        def fake_terminate():
            print("MOCK PROCESS TERMINATED")
            terminate_event.set()

        mock_process.wait.side_effect = fake_wait
        mock_process.terminate.side_effect = fake_terminate

        with patch('subprocess.Popen', return_value=mock_process):
            # Start an intervention
            intervention = {"type": "test_speech", "message": "This is a long speech."}
            app.intervention_engine.start_intervention(intervention)

            # Wait for it to start blocking
            if not blocking_event.wait(timeout=2):
                self.fail("Intervention did not start speaking (Popen not called).")

            print("Intervention is speaking (blocked). Initiating shutdown...")

            start_time = time.time()
            # Start shutdown in a thread so we can time it
            t = threading.Thread(target=app._shutdown)
            t.start()

            t.join(timeout=6)
            duration = time.time() - start_time

            if t.is_alive():
                print("FAILURE: Shutdown hung waiting for intervention.")
                self.fail("Shutdown hung.")
            else:
                print(f"Shutdown completed in {duration:.2f}s")

            # Verify terminate was called
            mock_process.terminate.assert_called()

if __name__ == '__main__':
    unittest.main()
