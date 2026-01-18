import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import collections

# Mock sounddevice before import
with patch.dict('sys.modules', {'sounddevice': MagicMock()}):
    from sensors.audio_sensor import AudioSensor

class TestAudioFeatures(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.sensor = AudioSensor(data_logger=self.logger)
        # Reset buffer to empty deque for clean state
        self.sensor.raw_audio_buffer = collections.deque(maxlen=self.sensor.buffer_size)
        self.sensor.stream = MagicMock()

    def test_pitch_estimation_sine_wave(self):
        """Verify that a pure sine wave results in the correct pitch estimation."""
        fs = 44100
        duration = 1.0 # seconds
        f0 = 440.0 # Hz
        t = np.arange(0, duration, 1/fs)
        # Generate sine wave with sufficient amplitude
        sine_wave = 0.5 * np.sin(2 * np.pi * f0 * t)

        chunk = sine_wave.reshape(-1, 1).astype(np.float32)

        # analyze_chunk updates internal buffer and returns metrics
        metrics = self.sensor.analyze_chunk(chunk)

        # Verify pitch (allow small delta for FFT resolution)
        self.assertAlmostEqual(metrics['pitch_estimation'], f0, delta=10.0)

    def test_speech_rate_bursts(self):
        """Verify that amplitude bursts are counted as speech rate."""
        fs = 44100
        duration = 1.0
        t = np.arange(0, duration, 1/fs)

        # Create bursts
        signal = np.random.normal(0, 0.01, size=len(t)) # Low noise floor
        for i in range(4):
            start = int((0.1 + i * 0.2) * fs)
            end = start + int(0.1 * fs) # 100ms burst
            signal[start:end] = np.random.normal(0, 0.5, end-start) # High amplitude

        chunk = signal.reshape(-1, 1).astype(np.float32)

        # Must populate internal buffer for speech rate calculation (which requires history)
        # analyze_chunk does this: self.raw_audio_buffer.extend(audio_data)
        metrics = self.sensor.analyze_chunk(chunk)

        # With 1 second of data, 4 bursts should give rate ~4.0
        # Allow range 3-5
        self.assertGreaterEqual(metrics['speech_rate'], 3.0)
        self.assertLessEqual(metrics['speech_rate'], 5.0)

    def test_silence(self):
        """Verify metrics for silence."""
        fs = 44100
        chunk = np.zeros((fs, 1), dtype=np.float32)

        metrics = self.sensor.analyze_chunk(chunk)

        self.assertAlmostEqual(metrics['rms'], 0.0, delta=0.001)
        self.assertEqual(metrics['speech_rate'], 0.0)
