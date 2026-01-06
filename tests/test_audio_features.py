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
        self.assertAlmostEqual(metrics['rms'], 0.0, places=4)
        self.assertEqual(metrics['speech_rate'], 0.0)
        # Check backward compatibility keys exist
        self.assertIn('activity_bursts', metrics)
        self.assertIn('rms_variance', metrics)

    def test_sine_wave_pitch(self):
        # Create 440Hz sine wave
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
    def test_speech_rate(self):
        # Generate synthetic speech syllables (amplitude bursts)
        fs = 44100
        duration = 1.0 # 1 second
        t = np.linspace(0, duration, int(fs*duration), endpoint=False)

        # Create 3 bursts in 1 second
        burst_signal = np.zeros_like(t)

        # Burst 1: 0.1s - 0.2s
        burst_signal[int(0.1*fs):int(0.2*fs)] = np.sin(2 * np.pi * 440 * t[int(0.1*fs):int(0.2*fs)])
        # Burst 2: 0.4s - 0.5s
        burst_signal[int(0.4*fs):int(0.5*fs)] = np.sin(2 * np.pi * 440 * t[int(0.4*fs):int(0.5*fs)])
        # Burst 3: 0.7s - 0.8s
        burst_signal[int(0.7*fs):int(0.8*fs)] = np.sin(2 * np.pi * 440 * t[int(0.7*fs):int(0.8*fs)])

        metrics = self.sensor.analyze_chunk(burst_signal)

        # We expect roughly 3 syllables per second
        self.assertAlmostEqual(metrics['speech_rate'], 3.0, delta=1.0) # Delta 1.0 to be safe (2-4 range)

    def test_speech_rate_streaming_small_chunks(self):
        # Test streaming logic with small chunks (e.g. 50ms)
        fs = 44100
        total_duration = 1.0
        t = np.linspace(0, total_duration, int(fs*total_duration), endpoint=False)

        # 3 bursts total in 1 second
        full_signal = np.zeros_like(t)
        full_signal[int(0.1*fs):int(0.2*fs)] = np.sin(2 * np.pi * 440 * t[int(0.1*fs):int(0.2*fs)])
        full_signal[int(0.4*fs):int(0.5*fs)] = np.sin(2 * np.pi * 440 * t[int(0.4*fs):int(0.5*fs)])
        full_signal[int(0.7*fs):int(0.8*fs)] = np.sin(2 * np.pi * 440 * t[int(0.7*fs):int(0.8*fs)])

        chunk_size = int(0.05 * fs) # 50ms chunks
        num_chunks = len(full_signal) // chunk_size

        final_rate = 0.0
        for i in range(num_chunks):
            chunk = full_signal[i*chunk_size : (i+1)*chunk_size]
            metrics = self.sensor.analyze_chunk(chunk)
            # Rate might be 0 until buffer fills, then stabilize
            if metrics['speech_rate'] > 0:
                final_rate = metrics['speech_rate']

        # After full second is buffered, rate should be approx 3.0
        # The buffer holds 1s, and we fed 1s.
        self.assertAlmostEqual(final_rate, 3.0, delta=1.0)

    def tearDown(self):
        self.sensor.release()

        self.assertAlmostEqual(metrics['rms'], 0.0, delta=0.001)
        self.assertEqual(metrics['speech_rate'], 0)
