import unittest
import numpy as np
from unittest.mock import MagicMock, patch

# Mock sounddevice before importing AudioSensor
with patch.dict('sys.modules', {'sounddevice': MagicMock()}):
    from sensors.audio_sensor import AudioSensor

try:
    from scipy import signal
except ImportError:
    signal = None

class TestVADLogic(unittest.TestCase):
    def setUp(self):
        self.sensor = AudioSensor(chunk_duration=1.0)
        self.sample_rate = self.sensor.sample_rate

    def test_silence(self):
        # Digital silence
        silence = np.zeros(self.sample_rate)
        is_speech, confidence = self.sensor._detect_voice_activity(silence)
        self.assertFalse(is_speech)
        self.assertLess(confidence, 0.5)

    def test_low_noise(self):
        # White noise at low level (simulating fan)
        # RMS ~ 0.005
        np.random.seed(42)
        noise = np.random.normal(0, 0.005, self.sample_rate)

        # Prime the history with this noise level
        for _ in range(10):
            self.sensor._detect_voice_activity(noise)

        is_speech, confidence = self.sensor._detect_voice_activity(noise)
        self.assertFalse(is_speech, "Low noise should not trigger VAD")

    def test_speech_burst(self):
        # Simulate speech: 400Hz tone at decent amplitude (0.1)
        # Note: 400Hz is within the 300-3400Hz band
        t = np.linspace(0, 1.0, self.sample_rate)
        speech = 0.1 * np.sin(2 * np.pi * 400 * t)

        # First ensure noise floor is low
        silence = np.zeros(self.sample_rate)
        for _ in range(10):
            self.sensor._detect_voice_activity(silence)

        is_speech, confidence = self.sensor._detect_voice_activity(speech)
        self.assertTrue(is_speech, "Speech signal should trigger VAD")
        self.assertGreater(confidence, 0.5)

    def test_out_of_band_noise(self):
        if signal is None:
            self.skipTest("scipy not installed, cannot test VAD filter")

        # High frequency hiss (e.g. 5000Hz) - should be attenuated by filter
        t = np.linspace(0, 1.0, self.sample_rate)
        hiss = 0.1 * np.sin(2 * np.pi * 5000 * t)

        # Prime history with silence
        for _ in range(10):
            self.sensor._detect_voice_activity(np.zeros(self.sample_rate))

        # The filter should attenuate this significantly
        # but pure sine wave at 0.1 is LOUD. Filter attenuation might not be infinite.
        # Check filtered energy directly if possible, or assume it reduces confidence.

        # Let's verify filter function first
        filtered = self.sensor._vad_filter(hiss)
        rms_raw = np.sqrt(np.mean(hiss**2))
        rms_filtered = np.sqrt(np.mean(filtered**2))

        # Butter filter at 3400Hz cut-off, 5000Hz signal should be attenuated
        self.assertLess(rms_filtered, rms_raw * 0.5, "Filter should attenuate out-of-band high frequencies")

        # Low frequency rumble (e.g. 50Hz)
        rumble = 0.1 * np.sin(2 * np.pi * 50 * t)
        filtered_rumble = self.sensor._vad_filter(rumble)
        rms_rumble = np.sqrt(np.mean(filtered_rumble**2))

        self.assertLess(rms_rumble, rms_raw * 0.1, "Filter should attenuate out-of-band low frequencies")

    def test_hangover(self):
        # Speech then silence
        t = np.linspace(0, 1.0, self.sample_rate)
        speech = 0.1 * np.sin(2 * np.pi * 400 * t)
        silence = np.zeros(self.sample_rate)

        # Prime with silence
        for _ in range(5):
             self.sensor._detect_voice_activity(silence)

        # Speech triggers VAD
        self.sensor._detect_voice_activity(speech)
        self.assertEqual(self.sensor.vad_hangover, self.sensor.vad_hangover_frames)

        # Immediate silence should still be True (hangover)
        is_speech, _ = self.sensor._detect_voice_activity(silence)
        self.assertTrue(is_speech, "Hangover should keep VAD true immediately after speech")

        # Burn through hangover
        for _ in range(self.sensor.vad_hangover_frames + 1):
             is_speech, _ = self.sensor._detect_voice_activity(silence)

        self.assertFalse(is_speech, "VAD should return to false after hangover expires")

if __name__ == '__main__':
    unittest.main()
