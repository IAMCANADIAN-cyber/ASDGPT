import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

# We need to mock sounddevice BEFORE importing AudioSensor because it might initialize things or fail if no device
with patch.dict('sys.modules', {'sounddevice': MagicMock()}):
    from sensors.audio_sensor import AudioSensor

class TestAudioFeatures(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.sensor = AudioSensor(self.logger)
        # Mock the stream to avoid actual hardware calls
        self.sensor.stream = MagicMock()

    def test_pitch_estimation_sine_wave(self):
        """Verify that a pure sine wave results in the correct pitch estimation."""
        fs = 44100
        duration = 1.0 # seconds
        f0 = 440.0 # Hz
        t = np.arange(0, duration, 1/fs)
        # Generate sine wave
        sine_wave = 0.5 * np.sin(2 * np.pi * f0 * t)

        # Inject into sensor buffer directly
        # The sensor likely stores raw data.
        # Note: buffer might be (N, 1) or (N,) depending on sounddevice callback.
        # usually sounddevice returns (frames, channels)
        self.sensor.raw_audio_buffer = sine_wave.reshape(-1, 1).astype(np.float32)

        # Call the internal analysis method directly or get_metrics if it triggers analysis
        # Assuming get_metrics computes on the fly or returns latest analysis
        metrics = self.sensor.analyze_chunk(self.sensor.raw_audio_buffer)

        # Allow some margin of error for FFT resolution
        self.assertAlmostEqual(metrics['pitch_estimation'], f0, delta=5.0)
        self.assertLess(metrics['pitch_variance'], 10.0) # Should be stable

    def test_speech_rate_bursts(self):
        """Verify that amplitude bursts are counted as speech rate."""
        fs = 44100
        duration = 1.0
        t = np.arange(0, duration, 1/fs)

        # Create 4 bursts of noise
        signal = np.zeros_like(t)
        # Ensure silence baseline is clean
        signal[:] = 0.01
        for i in range(4):
            start = int((0.15 + i * 0.2) * fs)
            end = start + int(0.1 * fs) # 100ms burst to pass window smoothing
            # Make sure burst is significant
            signal[start:end] = np.random.normal(0, 1.0, end-start)

        self.sensor.raw_audio_buffer = signal.reshape(-1, 1).astype(np.float32)

        metrics = self.sensor.analyze_chunk(self.sensor.raw_audio_buffer)

        # We expect around 4 bursts/sec
        self.assertGreaterEqual(metrics['speech_rate'], 3)
        self.assertLessEqual(metrics['speech_rate'], 5)

    def test_silence(self):
        """Verify metrics for silence."""
        self.sensor.raw_audio_buffer = np.zeros((44100, 1), dtype=np.float32)
        metrics = self.sensor.analyze_chunk(self.sensor.raw_audio_buffer)

        self.assertAlmostEqual(metrics['rms'], 0.0, delta=0.001)
        self.assertEqual(metrics['speech_rate'], 0)
