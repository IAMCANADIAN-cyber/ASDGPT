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
        self.assertEqual(metrics['activity_bursts'], 0)

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

    def tearDown(self):
        self.sensor.release()

if __name__ == '__main__':
    unittest.main()
