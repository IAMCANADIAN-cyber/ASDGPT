import sys
import os
import numpy as np
import unittest

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sensors.audio_sensor import AudioSensor
import config

class TestVADRefinement(unittest.TestCase):
    def setUp(self):
        # Mock logger
        class MockLogger:
            def log_info(self, m): pass
            def log_warning(self, m): pass
            def log_error(self, m, d=""): pass

        self.sensor = AudioSensor(data_logger=MockLogger(), sample_rate=16000, chunk_duration=0.5)

    def test_constant_hum_suppression(self):
        """
        Test if a constant frequency hum (fan noise) is suppressed.
        It should have low RMS variance and thus be penalized.

        This verifies that steady-state noise sources (like HVAC or computer fans)
        do not trigger VAD, improving overall system accuracy.
        """
        print("\n--- Test: Constant Hum (Fan) ---")
        t = np.linspace(0, self.sensor.chunk_duration, self.sensor.chunk_size, endpoint=False)
        chunk = 0.3 * np.sin(2 * np.pi * 120 * t)

        metrics = {}
        for i in range(10):
            metrics = self.sensor.analyze_chunk(chunk)
            print(f"Hum Chunk {i}: RMS={metrics['rms']:.3f}, Var={metrics['rms_variance']:.3f}, Conf={metrics['speech_confidence']:.2f}")

        # Should be suppressed (<= 0.4)
        self.assertLessEqual(metrics['speech_confidence'], 0.4)
        self.assertFalse(metrics['is_speech'])

    def test_dynamic_speech_proxy(self):
        """
        Test a signal that varies in amplitude over time (like real speech).
        It should have high RMS variance and thus NOT be penalized.
        """
        print("\n--- Test: Dynamic Speech Proxy ---")
        t = np.linspace(0, self.sensor.chunk_duration, self.sensor.chunk_size, endpoint=False)
        carrier = np.sin(2 * np.pi * 150 * t)

        # Amplitudes simulating syllabic speech structure
        amplitudes = [0.1, 0.5, 0.8, 0.2, 0.6, 0.0, 0.4, 0.7, 0.2, 0.1]

        metrics = {}
        for i, amp in enumerate(amplitudes):
            chunk = amp * carrier
            metrics = self.sensor.analyze_chunk(chunk)
            print(f"Speech Chunk {i} (Amp={amp}): RMS={metrics['rms']:.3f}, Var={metrics['rms_variance']:.3f}, Conf={metrics['speech_confidence']:.2f}")

        # Last chunk has accumulated history variance, so it should be confident
        self.assertTrue(metrics['is_speech'], "Dynamic speech-like signal SHOULD be detected")
        self.assertGreaterEqual(metrics['speech_confidence'], 0.8)

    def test_typing_noise_suppression(self):
        print("\n--- Test: Typing Noise ---")
        np.random.seed(42)
        chunk = np.random.normal(0, 0.01, self.sensor.chunk_size)
        for i in range(10):
            pos = np.random.randint(0, len(chunk)-100)
            chunk[pos:pos+50] += np.random.normal(0, 0.5, 50)

        metrics = self.sensor.analyze_chunk(chunk)
        print(f"Typing Chunk: RMS={metrics['rms']:.3f}, ZCR={metrics['zcr']:.3f}, Conf={metrics['speech_confidence']:.2f}")
        self.assertFalse(metrics['is_speech'])

    def tearDown(self):
        self.sensor.release()

if __name__ == '__main__':
    unittest.main()
