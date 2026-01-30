import unittest
import time
import numpy as np
from unittest.mock import MagicMock, patch
import sys
import queue

# Ensure sounddevice is mocked if not already
if 'sounddevice' not in sys.modules or not isinstance(sys.modules['sounddevice'], MagicMock):
    sys.modules['sounddevice'] = MagicMock()

import sounddevice as sd
from sensors.audio_sensor import AudioSensor

class TestAudioReliabilityReal(unittest.TestCase):
    def setUp(self):
        # Reset the mock for each test
        sd.reset_mock()
        # Mock query_devices to return something valid
        sd.query_devices.return_value = [{'name': 'Mock Device', 'max_input_channels': 1}]

    def test_initialization_uses_callback(self):
        """Verify AudioSensor initializes InputStream with a callback."""
        sensor = AudioSensor()

        # Check if InputStream was initialized
        self.assertTrue(sd.InputStream.called)

        # Get the kwargs passed to InputStream
        call_kwargs = sd.InputStream.call_args[1]

        # Assert 'callback' is in kwargs and is callable
        self.assertIn('callback', call_kwargs)
        self.assertTrue(callable(call_kwargs['callback']))

        # Cleanup
        sensor.release()

    def test_callback_puts_data_in_queue(self):
        """Verify the callback function places audio data into the internal queue."""
        sensor = AudioSensor()

        # Retrieve the callback function passed to InputStream
        call_kwargs = sd.InputStream.call_args[1]
        callback = call_kwargs['callback']

        # Setup mock stream to be active so get_chunk doesn't bail early
        # Note: sensor.stream is set to sd.InputStream return value
        mock_stream = sd.InputStream.return_value
        mock_stream.closed = False

        # Create dummy audio data
        chunk_size = sensor.chunk_size
        dummy_data = np.zeros((chunk_size, 1), dtype=np.float32)

        # Simulate callback invocation
        # Callback signature: indata, frames, time, status
        callback(dummy_data, chunk_size, None, None)

        # Now check if get_chunk returns this data
        chunk, error = sensor.get_chunk()

        self.assertIsNotNone(chunk)
        self.assertIsNone(error)
        np.testing.assert_array_equal(chunk, dummy_data)

        sensor.release()

    def test_get_chunk_non_blocking_behavior(self):
        """Verify get_chunk returns None immediately (or after short timeout) if no data."""
        sensor = AudioSensor()

        # Setup mock stream to be active
        mock_stream = sd.InputStream.return_value
        mock_stream.closed = False

        start_time = time.time()
        chunk, error = sensor.get_chunk()
        duration = time.time() - start_time

        # Should return None, None because queue is empty
        self.assertIsNone(chunk)
        self.assertIsNone(error)

        # Assert it didn't block for long (timeout is chunk_duration * 1.5, which is 1.5s default)
        # But wait, default chunk_duration is 1.0s. So timeout is 1.5s.
        # This test might be slow if we wait for full timeout.
        # We should set a shorter chunk duration for test or assert it respected the timeout.

        # To speed up test, let's re-init sensor with short chunk_duration
        sensor = AudioSensor(chunk_duration=0.1)
        mock_stream = sd.InputStream.return_value
        mock_stream.closed = False

        start_time = time.time()
        chunk, error = sensor.get_chunk()
        duration = time.time() - start_time

        # Expect timeout ~0.15s
        self.assertLess(duration, 0.3)
        self.assertIsNone(chunk)

        sensor.release()

    def test_release_stops_stream(self):
        """Verify release calls stop/close on the stream."""
        sensor = AudioSensor()

        # Mock the stream instance returned by InputStream
        mock_stream = sd.InputStream.return_value
        # Important: set closed=False so release() attempts to close it
        mock_stream.closed = False

        sensor.release()

        # Verify stop and close were called
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

        # Verify stream is set to None
        self.assertIsNone(sensor.stream)

if __name__ == '__main__':
    unittest.main()
