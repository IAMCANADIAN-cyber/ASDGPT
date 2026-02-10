import unittest
import numpy as np
from unittest.mock import MagicMock
from sensors.audio_sensor import AudioSensor

class TestAudioFeatures(unittest.TestCase):
    def setUp(self):
        self.sensor = AudioSensor(chunk_duration=0.1, history_seconds=1)
        # Mock stream to avoid hardware init and errors in release
        self.sensor.stream = MagicMock()
        self.sensor.stream.closed = False
        self.sensor.error_state = False

    def test_silence(self):
        # Create silent chunk
        chunk = np.zeros(4410)
        metrics = self.sensor.analyze_chunk(chunk)

        self.assertAlmostEqual(metrics['rms'], 0.0, places=4)
        self.assertEqual(metrics['speech_rate'], 0.0)
        # Check backward compatibility keys exist
        self.assertIn('activity_bursts', metrics)
        self.assertIn('rms_variance', metrics)

    def test_sine_wave_pitch(self):
        # Create 440Hz sine wave
        fs = 44100
        duration = 0.1
        t = np.linspace(0, duration, int(fs*duration), endpoint=False)
        chunk = 0.5 * np.sin(2 * np.pi * 440 * t)

        metrics = self.sensor.analyze_chunk(chunk)

        # Pitch should be close to 440
        # FFT resolution depends on window size. with 0.1s, resolution is ~10Hz
        self.assertTrue(400 < metrics['pitch_estimation'] < 480, f"Pitch {metrics['pitch_estimation']} not close to 440")

        # RMS should be ~0.5 / sqrt(2) = 0.3535
        self.assertAlmostEqual(metrics['rms'], 0.3535, places=1)

    def test_pitch_interpolation(self):
        # 445 Hz is exactly between 440Hz (bin 44) and 450Hz (bin 45) for 0.1s chunk at 44100Hz
        fs = 44100
        duration = 0.1
        t = np.linspace(0, duration, int(fs*duration), endpoint=False)

        # Use a pure sine wave at 445 Hz
        target_freq = 445.0
        chunk = 0.5 * np.sin(2 * np.pi * target_freq * t)

        metrics = self.sensor.analyze_chunk(chunk)
        estimated_pitch = metrics['pitch_estimation']

        # We assert that the error is less than 1.0 Hz (verifies interpolation works)
        self.assertLess(abs(estimated_pitch - target_freq), 1.0,
                        f"Pitch estimation error too high: {abs(estimated_pitch - target_freq)} Hz. Expected close to 0.")

    def test_pitch_variance(self):
        # Generate two chunks with different pitches to trigger variance
        fs = 44100
        duration = 0.1
        t = np.linspace(0, duration, int(fs*duration), endpoint=False)

        chunk1 = 0.5 * np.sin(2 * np.pi * 440 * t) # 440 Hz
        chunk2 = 0.5 * np.sin(2 * np.pi * 880 * t) # 880 Hz

        self.sensor.analyze_chunk(chunk1)
        self.sensor.analyze_chunk(chunk2)

        # Add a third to ensure history > 2 calculation
        self.sensor.analyze_chunk(chunk1)

        metrics = self.sensor.analyze_chunk(chunk1) # 4th call

        self.assertGreater(metrics['pitch_variance'], 0)

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

if __name__ == '__main__':
    unittest.main()
