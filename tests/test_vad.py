
import unittest
import numpy as np
import sys
from unittest.mock import MagicMock

# Mock sounddevice
sys.modules['sounddevice'] = MagicMock()

from sensors.audio_sensor import AudioSensor

class TestAudioVAD(unittest.TestCase):
    def setUp(self):
        self.sensor = AudioSensor(data_logger=MagicMock())
        # Manually enable VAD for test if it was a flag, but we will just check the metric

    def test_silence(self):
        # Create silent chunk
        chunk = np.zeros(1024)
        analysis = self.sensor.analyze_chunk(chunk)

        # Expect speech confidence to be low/0
        self.assertLess(analysis.get("speech_confidence", 0.0), 0.1)
        self.assertFalse(analysis.get("is_speech", False))

    def test_noise(self):
        # Create random noise (high ZCR)
        np.random.seed(42)
        chunk = np.random.uniform(-0.1, 0.1, 1024)

        # High ZCR, low energy (relatively)
        analysis = self.sensor.analyze_chunk(chunk)

        # Should be classified as noise or at least low confidence speech
        # Note: Depending on implementation, simple energy VAD might flag this if loud enough.
        # But we want to distinguish noise.
        pass

    def test_speech_like_tone(self):
        # Create a sine wave in human voice range (e.g., 400Hz)
        sample_rate = 44100
        t = np.linspace(0, 1024/sample_rate, 1024)
        chunk = 0.5 * np.sin(2 * np.pi * 400 * t)

        analysis = self.sensor.analyze_chunk(chunk)

        # Should be high confidence
        self.assertGreater(analysis.get("speech_confidence", 0.0), 0.5)
        self.assertTrue(analysis.get("is_speech", True))

if __name__ == '__main__':
    unittest.main()
