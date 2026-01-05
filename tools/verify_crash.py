
import sys
import time
import threading
import unittest
from unittest.mock import MagicMock, patch

# 1. Mock system/hardware dependencies BEFORE importing application code
sys.modules['cv2'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['keyboard'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()

# Mock config
sys.modules['config'] = MagicMock()
sys.modules['config'].LOG_FILE = "test_crash.log"
sys.modules['config'].LOG_LEVEL = "INFO"
sys.modules['config'].CAMERA_INDEX = 0
sys.modules['config'].SNOOZE_DURATION = 300
sys.modules['config'].LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
sys.modules['config'].LMM_CIRCUIT_BREAKER_COOLDOWN = 60
sys.modules['config'].AUDIO_THRESHOLD_HIGH = 0.5
sys.modules['config'].VIDEO_ACTIVITY_THRESHOLD_HIGH = 10
sys.modules['config'].DEFAULT_MODE = "active"
sys.modules['config'].HOTKEY_CYCLE_MODE = "ctrl+alt+m"
sys.modules['config'].HOTKEY_PAUSE_RESUME = "ctrl+alt+p"
sys.modules['config'].HOTKEY_FEEDBACK_HELPFUL = "ctrl+alt+h"
sys.modules['config'].HOTKEY_FEEDBACK_UNHELPFUL = "ctrl+alt+u"
sys.modules['config'].FEEDBACK_WINDOW_SECONDS = 15

# Mock Sensor Classes
mock_video_sensor_cls = MagicMock()
mock_audio_sensor_cls = MagicMock()

# Setup instances with blocking/slow behavior using Event
# We use an event to simulate blocking that can be interrupted by release
video_release_event = threading.Event()
audio_release_event = threading.Event()

mock_video_instance = MagicMock()
def slow_get_frame():
    # Wait for 10s OR until release event is set
    if not video_release_event.wait(timeout=10.0):
        # Timed out (still blocking)
        pass
    return (None, None)

mock_video_instance.get_frame.side_effect = slow_get_frame
mock_video_instance.has_error.return_value = False
mock_video_instance.process_frame.return_value = {"video_activity": 0.0, "face_detected": False}
def video_release():
    video_release_event.set()
mock_video_instance.release.side_effect = video_release

mock_audio_instance = MagicMock()
def slow_get_chunk():
    if not audio_release_event.wait(timeout=10.0):
        pass
    return (None, None)
mock_audio_instance.get_chunk.side_effect = slow_get_chunk
mock_audio_instance.has_error.return_value = False
mock_audio_instance.analyze_chunk.return_value = {"rms": 0.0}
def audio_release():
    audio_release_event.set()
mock_audio_instance.release.side_effect = audio_release


mock_video_sensor_cls.return_value = mock_video_instance
mock_audio_sensor_cls.return_value = mock_audio_instance

sys.modules['sensors.video_sensor'] = MagicMock()
sys.modules['sensors.video_sensor'].VideoSensor = mock_video_sensor_cls
sys.modules['sensors.audio_sensor'] = MagicMock()
sys.modules['sensors.audio_sensor'].AudioSensor = mock_audio_sensor_cls

# Mock DataLogger
mock_logger = MagicMock()
sys.modules['core.data_logger'] = MagicMock()
sys.modules['core.data_logger'].DataLogger = MagicMock(return_value=mock_logger)

# Now import the application class
sys.path.append('.')
from main import Application

class TestReliability(unittest.TestCase):
    def setUp(self):
        mock_video_instance.reset_mock()
        mock_audio_instance.reset_mock()
        video_release_event.clear()
        audio_release_event.clear()

    def test_rapid_start_stop_with_blocking_sensors(self):
        """
        Starts and stops the application.
        Simulates blocking sensors (10s delay).
        Fails if worker threads are still alive after shutdown (timeout 2s).

        Currently main.py calls join() BEFORE release().
        So release() is not called until join times out.
        So threads will be blocked for 2s (timeout), then release called, then they exit.

        Wait, if release is called AFTER timeout, the thread will eventually exit.
        But at the moment join() returns, the thread is still alive?
        join() blocks until thread terminates or timeout.
        If timeout, join returns, thread is ALIVE.
        Then release() is called.
        Then thread exits (because we wired release to unblock).

        So if we check alive immediately after app.run() returns, it might be dead because release() was called.

        BUT, the shutdown process takes 2s + 2s = 4s waiting for timeouts.
        We want shutdown to be fast!

        If we move release() before join(), shutdown should be instant (ms), because release unblocks thread, thread exits, join returns immediately.

        So we can assert that shutdown took < 1s.
        """
        # Run 1 cycle
        for i in range(1, 2):
            app = Application()

            run_thread = threading.Thread(target=app.run, daemon=True)
            run_thread.start()

            # Let it run
            time.sleep(0.5)

            start_time = time.time()
            # Initiate shutdown
            app.quit_application()

            # Wait for run_thread to finish
            run_thread.join(timeout=10.0)
            end_time = time.time()

            duration = end_time - start_time
            print(f"Shutdown took {duration:.2f} seconds")

            if run_thread.is_alive():
                self.fail(f"Cycle {i}: Main loop failed to exit.")

            # If shutdown took > 2s, it means we hit the timeouts because release wasn't called first.
            if duration > 1.5:
                self.fail(f"Cycle {i}: Shutdown took too long ({duration:.2f}s). Likely waiting for thread timeouts instead of releasing sensors.")

            if app.video_thread and app.video_thread.is_alive():
                self.fail(f"Cycle {i}: Video worker thread is still alive (Zombie)!")

            if app.audio_thread and app.audio_thread.is_alive():
                self.fail(f"Cycle {i}: Audio worker thread is still alive (Zombie)!")

if __name__ == '__main__':
    unittest.main()
