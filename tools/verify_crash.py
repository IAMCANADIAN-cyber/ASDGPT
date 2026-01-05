import unittest
from unittest.mock import MagicMock, patch
import time
import sys
import threading
import queue

# Mock dependencies to allow running in CI/headless environments
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['scipy.io.wavfile'] = MagicMock()

from main import Application
from sensors.audio_sensor import AudioSensor
from sensors.video_sensor import VideoSensor

class TestLifecycle(unittest.TestCase):
    def setUp(self):
        self.mock_sd = sys.modules['sounddevice']
        self.mock_cv2 = sys.modules['cv2']
        self.mock_sd.PortAudioError = Exception # Mock exception class

    @patch('main.Application._setup_hotkeys')
    def test_shutdown_order(self, mock_hotkeys):
        """Verify sensors are released BEFORE threads are joined to prevent zombie threads."""
        app = Application()

        # Mock sensors and threads
        app.video_sensor = MagicMock()
        app.audio_sensor = MagicMock()

        video_thread = MagicMock()
        video_thread.is_alive.return_value = True
        app.video_thread = video_thread

        audio_thread = MagicMock()
        audio_thread.is_alive.return_value = True
        app.audio_thread = audio_thread

        # Track call order using a shared mock manager
        manager = MagicMock()
        manager.attach_mock(app.video_sensor.release, 'video_release')
        manager.attach_mock(app.audio_sensor.release, 'audio_release')
        manager.attach_mock(video_thread.join, 'video_join')
        manager.attach_mock(audio_thread.join, 'audio_join')

        # Execute shutdown
        app._shutdown()

        # Assertions
        calls = manager.mock_calls
        release_indices = [i for i, c in enumerate(calls) if 'release' in c[0]]
        join_indices = [i for i, c in enumerate(calls) if 'join' in c[0]]

        self.assertTrue(len(release_indices) > 0, "Sensors must be released.")
        self.assertTrue(len(join_indices) > 0, "Threads must be joined.")
        self.assertTrue(max(release_indices) < min(join_indices),
                        "All sensor releases must occur before any thread joins.")

    def test_audio_sensor_safe_release(self):
        """Test AudioSensor handles release during active use safely."""
        sensor = AudioSensor()
        # Mock the stream
        mock_stream = MagicMock()
        mock_stream.closed = False
        sensor.stream = mock_stream

        # Simulate release
        sensor.release()

        mock_stream.stop.assert_called()
        mock_stream.close.assert_called()
        self.assertIsNone(sensor.stream)

    def test_video_sensor_error_state(self):
        """Test VideoSensor error state tracking."""
        # Ensure face cascade mock reports not empty so init succeeds without error
        cascade_mock = self.mock_cv2.CascadeClassifier.return_value
        cascade_mock.empty.return_value = False

        sensor = VideoSensor()
        self.assertFalse(sensor.has_error())

        sensor._log_error("Test error")
        self.assertTrue(sensor.has_error())
        self.assertEqual(sensor.get_last_error(), "Test error")

        sensor.release()
        self.assertFalse(sensor.has_error(), "Error state should clear on release/reset")

if __name__ == '__main__':
    unittest.main()
