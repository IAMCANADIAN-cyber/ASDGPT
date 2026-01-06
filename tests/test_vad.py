import sys
import os
import numpy as np
import unittest

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sensors.audio_sensor import AudioSensor
import config

class TestVAD(unittest.TestCase):
    def setUp(self):
        # Mock logger
        class MockLogger:
            def log_info(self, m): pass
            def log_warning(self, m): pass
            def log_error(self, m, d=""): pass

        self.sensor = AudioSensor(data_logger=MockLogger(), sample_rate=16000)

    def test_silence(self):
        # Generate silence (zeros)
        chunk = np.zeros(self.sensor.chunk_size)
        metrics = self.sensor.analyze_chunk(chunk)

        print(f"Silence Metrics: RMS={metrics.get('rms')}, Conf={metrics.get('speech_confidence')}")
        self.assertIn('speech_confidence', metrics)
        self.assertIn('is_speech', metrics)
        self.assertLess(metrics['speech_confidence'], 0.1)
        self.assertFalse(metrics['is_speech'])

    def test_pure_tone_speech_range(self):
        # Generate 150Hz sine wave (typical male fundamental freq)
        t = np.linspace(0, self.sensor.chunk_duration, self.sensor.chunk_size, endpoint=False)
        chunk = 0.5 * np.sin(2 * np.pi * 150 * t) # Amplitude 0.5

        metrics = self.sensor.analyze_chunk(chunk)
        print(f"Tone (150Hz) Metrics: RMS={metrics.get('rms'):.4f}, Pitch={metrics.get('pitch_estimation'):.1f}, ZCR={metrics.get('zcr'):.4f}, Conf={metrics.get('speech_confidence')}")

        # Should be detected as potential speech (voiced)
        self.assertIn('speech_confidence', metrics)
        self.assertGreater(metrics['speech_confidence'], 0.5)
        self.assertTrue(metrics['is_speech'])

    def test_white_noise(self):
        # Generate white noise (random) - High ZCR, High Energy
        np.random.seed(42)
        chunk = np.random.uniform(-0.5, 0.5, self.sensor.chunk_size)

        metrics = self.sensor.analyze_chunk(chunk)
        print(f"Noise Metrics: RMS={metrics.get('rms'):.4f}, Pitch={metrics.get('pitch_estimation'):.1f}, ZCR={metrics.get('zcr'):.4f}, Conf={metrics.get('speech_confidence')}")

        # Should have low confidence (high ZCR usually indicates noise or unvoiced consonants,
        # but sustained high ZCR without pitch structure is likely noise)
        # Note: Unvoiced consonants (s, sh) are speech, but standalone noise is not.
        # Simple VAD might struggle here, but confidence should be lower than pure tone.
        self.assertLess(metrics['speech_confidence'], 0.6)

    def tearDown(self):
        self.sensor.release()

if __name__ == '__main__':
    unittest.main()
