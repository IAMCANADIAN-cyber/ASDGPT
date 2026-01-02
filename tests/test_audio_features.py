import unittest
import numpy as np
from sensors.audio_sensor import AudioSensor

class MockLogger:
    def log_info(self, msg): pass
    def log_warning(self, msg): pass
    def log_error(self, msg, details=""): pass

class TestAudioFeatures(unittest.TestCase):
    def setUp(self):
        self.sensor = AudioSensor(data_logger=MockLogger(), chunk_duration=0.1)
        # Mock stream so we don't need real hardware
        self.sensor.stream = None

    def test_silence(self):
        chunk = np.zeros(4410) # 0.1s at 44.1k
        metrics = self.sensor.analyze_chunk(chunk)
        self.assertAlmostEqual(metrics['rms'], 0.0)
        self.assertAlmostEqual(metrics['zcr'], 0.0)
        self.assertAlmostEqual(metrics['spectral_centroid'], 0.0)

    def test_sine_wave(self):
        # Generate 440Hz sine wave
        fs = 44100
        duration = 0.5
        t = np.linspace(0, duration, int(fs*duration), endpoint=False)
        freq = 440
        chunk = 0.5 * np.sin(2 * np.pi * freq * t)

        metrics = self.sensor.analyze_chunk(chunk)

        # RMS should be amplitude / sqrt(2) = 0.5 * 0.707 = 0.3535
        self.assertAlmostEqual(metrics['rms'], 0.5 * 0.7071, places=2)

        # Pitch should be approx 440
        self.assertTrue(430 < metrics['pitch_estimation'] < 450, f"Pitch {metrics['pitch_estimation']} not close to 440")

        # Spectral Centroid for pure sine should be close to freq
        self.assertTrue(430 < metrics['spectral_centroid'] < 450, f"Centroid {metrics['spectral_centroid']} not close to 440")

    def test_noise(self):
        # Random noise
        np.random.seed(42)
        chunk = np.random.uniform(-0.5, 0.5, 44100)
        metrics = self.sensor.analyze_chunk(chunk)

        # ZCR for white noise should be high (around 0.5 for uniform)
        # But theoretical expected ZCR for uniform noise is around 0.5?
        # Actually for uniform [-a, a], probability of crossing 0 is related.
        # Let's just check it's non-zero and "noisy" (e.g. > 0.1)
        self.assertGreater(metrics['zcr'], 0.1)
        self.assertGreater(metrics['spectral_centroid'], 1000) # Centroid of white noise is high (fs/4 approx?)

if __name__ == '__main__':
    unittest.main()
