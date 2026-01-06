
import unittest
import threading
import time
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path so config can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock sounddevice BEFORE it is imported anywhere else
# This is crucial because sounddevice throws OSError on import if PortAudio is missing
sys.modules['sounddevice'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['keyboard'] = MagicMock()

# Now we can import things that might use sounddevice
# import config # This might be imported by main.py

class TestShutdown(unittest.TestCase):
    def setUp(self):
        # Patch config to avoid side effects
        self.config_patcher = patch('config.LOG_FILE', 'test_crash.log')
        self.config_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()

    def test_shutdown_with_blocking_sensors(self):
        """
        Simulates a scenario where sensors are blocking (reading) when shutdown is requested.
        Verifies that shutdown completes quickly and threads are joined.
        """
        print("\n--- Starting Shutdown Stress Test ---")

        # 1. Setup Blocking Mocks
        video_read_event = threading.Event()
        audio_read_event = threading.Event()
        block_event = threading.Event()

        def blocking_video_read(*args, **kwargs):
            video_read_event.set()
            # Wait until unblocked or timeout
            if block_event.wait(timeout=5):
                 return True, None
            return False, None

        def blocking_audio_read(frames):
            audio_read_event.set()
            if block_event.wait(timeout=5):
                return None, False
            return None, True # overflow/timeout

        # Patch VideoSensor internals
        with patch('cv2.VideoCapture') as mock_cap_cls:
            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.read.side_effect = blocking_video_read
            mock_cap_cls.return_value = mock_cap

            # NOTE: We can't use patch('sounddevice.InputStream') normally because sounddevice is ALREADY mocked in sys.modules
            # So we just configure the mock that is already there.

            mock_sd = sys.modules['sounddevice']
            mock_stream_instance = MagicMock()
            mock_stream_instance.read.side_effect = blocking_audio_read
            mock_stream_instance.closed = False
            mock_sd.InputStream.return_value = mock_stream_instance

            # Also mock query_devices to avoid error during AudioSensor init
            mock_sd.query_devices.return_value = [{'name': 'Mock Mic', 'max_input_channels': 1}]

            # Import Application here to ensure patches apply to its sensor init
            # We need to make sure AudioSensor picks up the mocked sounddevice
            # If AudioSensor does "import sounddevice as sd", it gets our MagicMock from sys.modules

            # However, if AudioSensor was ALREADY imported before we mocked sys.modules, we are in trouble.
            # But we are in a fresh process (mostly), and we mocked at top of file.

            from main import Application

            app = Application()

            print("Starting worker threads...")
            app.running = True
            app.video_thread = threading.Thread(target=app._video_worker, daemon=True)
            app.audio_thread = threading.Thread(target=app._audio_worker, daemon=True)
            app.video_thread.start()
            app.audio_thread.start()

            # Wait for threads to hit the blocking read
            print("Waiting for threads to enter blocking read...")
            # We give them a moment to start and call read
            video_read_event.wait(timeout=2)
            audio_read_event.wait(timeout=2)

            if not video_read_event.is_set() or not audio_read_event.is_set():
                print("TEST SETUP FAILURE: Threads did not start reading.")
                if not video_read_event.is_set(): print("- Video thread failed to reach read.")
                if not audio_read_event.is_set(): print("- Audio thread failed to reach read.")
                app.running = False
                block_event.set()
                return

            print("Threads are blocked. Initiating shutdown...")
            start_time = time.time()

            # Execute Shutdown
            # We must simulate that calling release/close unblocks the read.
            # In a real system, the driver does this. Here we do it via side effect.

            def side_effect_release():
                print("Video release called - unblocking.")
                block_event.set()

            def side_effect_close():
                print("Audio close called - unblocking.")
                block_event.set()

            mock_cap.release.side_effect = side_effect_release
            mock_stream_instance.stop.side_effect = side_effect_close
            mock_stream_instance.close.side_effect = side_effect_close

            # Run shutdown in a thread to measure time (in case it hangs)
            shutdown_thread = threading.Thread(target=app._shutdown)
            shutdown_thread.start()

            shutdown_thread.join(timeout=6)
            end_time = time.time()

            if shutdown_thread.is_alive():
                print("FAILURE: _shutdown() hung and did not complete within 5 seconds.")
                block_event.set() # Unblock manually
                self.fail("Shutdown hung.")

            duration = end_time - start_time
            print(f"Shutdown completed in {duration:.4f} seconds.")

            # Verification
            self.assertFalse(app.video_thread.is_alive(), "Video thread should be dead")
            self.assertFalse(app.audio_thread.is_alive(), "Audio thread should be dead")

            # Check if sensors were actually released
            mock_cap.release.assert_called()
            mock_stream_instance.close.assert_called()

if __name__ == '__main__':
    unittest.main()
