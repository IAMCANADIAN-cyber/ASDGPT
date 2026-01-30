import unittest
from unittest.mock import patch, MagicMock
import os
import time
import threading
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import after path setup
import config
from sensors.audio_sensor import AudioSensor
from sensors.video_sensor import VideoSensor
from core.lmm_interface import LMMInterface

class TestLifecycle(unittest.TestCase):

    def test_config_loading(self):
        """Verify that config loads correctly and duplicates are gone (implicit by import)."""
        # We can't easily check for duplicates in the file structure via import,
        # but we can check values are what we expect.
        # Assuming no env vars set for this test run in sandbox except what we see.
        self.assertTrue(isinstance(config.AUDIO_THRESHOLD_HIGH, float))
        self.assertTrue(isinstance(config.VIDEO_ACTIVITY_THRESHOLD_HIGH, float))
        self.assertTrue(hasattr(config, 'LMM_CIRCUIT_BREAKER_COOLDOWN'))

    @patch('sensors.audio_sensor.sd')
    def test_audio_sensor_lifecycle(self, mock_sd):
        """Verify AudioSensor stop/release is idempotent and safe."""
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        # Mock 'closed' attribute not existing on stream object initially to simulate some backends,
        # or existing. The code handles both. Let's say it doesn't exist.
        del mock_stream.closed

        sensor = AudioSensor(data_logger=MagicMock())
        self.assertIsNotNone(sensor.stream)

        # Test stop
        sensor.stop()
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        self.assertIsNone(sensor.stream)

        # Test double stop (idempotency)
        try:
            sensor.stop()
        except Exception as e:
            self.fail(f"AudioSensor.stop() raised exception on second call: {e}")

    @patch('sensors.video_sensor.cv2')
    def test_video_sensor_lifecycle(self, mock_cv2):
        """Verify VideoSensor stop/release is idempotent."""
        mock_cap = MagicMock()
        mock_cv2.VideoCapture.return_value = mock_cap

        sensor = VideoSensor(camera_index=0, data_logger=MagicMock())
        self.assertIsNotNone(sensor.cap)

        # Test stop
        sensor.stop()
        mock_cap.release.assert_called_once()
        self.assertIsNone(sensor.cap)

        # Test double stop
        try:
            sensor.stop()
        except Exception as e:
            self.fail(f"VideoSensor.stop() raised exception on second call: {e}")

    @patch('core.lmm_interface.requests.post')
    def test_lmm_connection_error(self, mock_post):
        """Verify LMMInterface handles connection errors gracefully."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        logger = MagicMock()
        lmm = LMMInterface(data_logger=logger)

        # Disable fallback to strictly check for failure return if we wanted that,
        # OR check that it returns fallback response.
        # Let's check that it returns fallback response AND logs the specific error.

        # Speed up retries
        with patch('time.sleep'):
            res = lmm.process_data(user_context={"sensor_metrics": {}})

        # Expect fallback response if LMM_FALLBACK_ENABLED is True (default)
        if config.LMM_FALLBACK_ENABLED:
            self.assertIsNotNone(res)
            self.assertTrue(res.get('_meta', {}).get('is_fallback', False))
        else:
            self.assertIsNone(res)

        # Verify log warning contained "Connection Error"
        found_msg = False
        for call in logger.log_warning.call_args_list:
            if "Connection Error" in call[0][0]:
                found_msg = True
                break
        self.assertTrue(found_msg, "Did not find expected Connection Error log message.")

if __name__ == '__main__':
    unittest.main()
