
import unittest
import threading
import time
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies that might not exist or require hardware
sys.modules['pystray'] = MagicMock()
# sys.modules['keyboard'] = MagicMock() # Mocked inside main.py try-except usually, but let's be safe if we need to
# We need to mock cv2 and sounddevice to control their blocking behavior

class TestShutdown(unittest.TestCase):
    def setUp(self):
        # Patch config to avoid side effects
        self.config_patcher = patch('config.LOG_FILE', 'test_crash.log')
        self.config_patcher.start()

        # Patch keyboard import inside main by mocking sys.modules['keyboard'] if main imports it dynamically
        # main.py does 'import keyboard' inside _setup_hotkeys try-except
        # But patching main.keyboard directly fails if it hasn't been imported yet.
        # We can mock sys.modules['keyboard'] to ensure it's available and valid.
        sys.modules['keyboard'] = MagicMock()


    def tearDown(self):
        self.config_patcher.stop()

    def test_shutdown_with_blocking_sensors(self):
        """
        Simulates a scenario where sensors are blocking (reading) when shutdown is requested.
        Verifies that shutdown completes quickly and threads are joined.
        """
        print("\n--- Starting Shutdown Stress Test ---")

        # 1. Setup Blocking Mocks
        # Event to signal when the read is called
        video_read_event = threading.Event()
        audio_read_event = threading.Event()

        # Event to hold the read (simulate blocking)
        block_event = threading.Event()

        def blocking_video_read(*args, **kwargs):
            video_read_event.set()
            # Wait until unblocked or timeout (timeout prevents test hanging forever on failure)
            # The logic here is: if we wait on this event, the thread IS blocked.
            # It will only unblock if block_event is set.
            if block_event.wait(timeout=5):
                 return True, None
            return False, None

        def blocking_audio_read(frames):
            audio_read_event.set()
            if block_event.wait(timeout=5):
                return None, False
            return None, True # overflow/timeout

        # Patch VideoSensor internals
        # We need to patch cv2.VideoCapture to return our mock
        with patch('cv2.VideoCapture') as mock_cap_cls:
            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.read.side_effect = blocking_video_read
            mock_cap_cls.return_value = mock_cap

            # Patch AudioSensor internals
            with patch('sounddevice.InputStream') as mock_stream_cls:
                mock_stream = MagicMock()
                mock_stream.read.side_effect = blocking_audio_read
                # Important: stream.active should be true? or closed false?
                mock_stream.closed = False
                mock_stream_cls.return_value = mock_stream

                # Import Application here to ensure patches apply to its sensor init
                from main import Application

                app = Application()

                # We don't want to run the full app.run() loop because it blocks.
                # We just want to start the worker threads.
                # But app.run() starts them.
                # We can manually start them for this test.

                print("Starting worker threads...")
                app.running = True
                app.video_thread = threading.Thread(target=app._video_worker, daemon=True)
                app.audio_thread = threading.Thread(target=app._audio_worker, daemon=True)
                app.video_thread.start()
                app.audio_thread.start()

                # Wait for threads to hit the blocking read
                print("Waiting for threads to enter blocking read...")
                video_read_event.wait(timeout=2)
                audio_read_event.wait(timeout=2)

                if not video_read_event.is_set() or not audio_read_event.is_set():
                    print("TEST SETUP FAILURE: Threads did not start reading.")
                    app.running = False
                    block_event.set() # Release anyway
                    return

                print("Threads are blocked. Initiating shutdown...")
                start_time = time.time()

                # Execute Shutdown
                # This should:
                # 1. Set running = False (via quit_application)
                # 2. Release sensors (which should unblock the reads!)
                # 3. Join threads

                # Note: In the CURRENT broken implementation, it tries to join BEFORE releasing.
                # Since we mocked read to wait on 'block_event', and 'block_event' is only set if we explicitly set it
                # OR if the release method does something to unblock it.
                # But here, our mock 'read' waits on a python Event.
                # Real drivers unblock on release/close.
                # To simulate real driver behavior: calling release() on the mock should set block_event!

                def side_effect_release():
                    print("Video release called - unblocking.")
                    block_event.set()

                def side_effect_close():
                    print("Audio close called - unblocking.")
                    block_event.set()

                mock_cap.release.side_effect = side_effect_release
                mock_stream.stop.side_effect = side_effect_close
                mock_stream.close.side_effect = side_effect_close

                # Run shutdown in a thread to measure time (in case it hangs)
                shutdown_thread = threading.Thread(target=app._shutdown)
                shutdown_thread.start()

                shutdown_thread.join(timeout=6) # Slightly longer than block timeout
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
                mock_stream.close.assert_called()

if __name__ == '__main__':
    unittest.main()
