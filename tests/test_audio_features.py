import unittest
from unittest.mock import Mock, patch
import numpy as np
import collections
from sensors.audio_sensor import AudioSensor

class TestAudioSensorFeatures(unittest.TestCase):
    def setUp(self):
        self.mock_logger = Mock()
        # chunk_duration=1.0, history_seconds=5 => history_size=5
        self.sensor = AudioSensor(data_logger=self.mock_logger, chunk_duration=1.0, history_seconds=5)
        # Mock stream to avoid hardware errors
        self.sensor.stream = Mock()
        self.sensor.stream.closed = False

    def tearDown(self):
        if self.sensor.stream:
            self.sensor.stream.close()

    def test_initialization(self):
        self.assertEqual(self.sensor.history_size, 5)
        self.assertIsInstance(self.sensor.pitch_history, collections.deque)
        self.assertIsInstance(self.sensor.rms_history, collections.deque)

    def test_silence_metrics(self):
        # Silence chunk (zeros)
        chunk = np.zeros(self.sensor.chunk_size)
        metrics = self.sensor.analyze_chunk(chunk)

        self.assertAlmostEqual(metrics['rms'], 0.0)
        self.assertAlmostEqual(metrics['pitch_variance'], 0.0)
        self.assertEqual(metrics['activity_bursts'], 0)

        # Verify history update
        self.assertEqual(len(self.sensor.rms_history), 1)
        self.assertEqual(self.sensor.rms_history[-1], 0.0)
        # Pitch history shouldn't update on silence (pitch=0)
        self.assertEqual(len(self.sensor.pitch_history), 0)

    def test_constant_tone_variance(self):
        # Create a sine wave (constant pitch)
        t = np.linspace(0, 1.0, self.sensor.chunk_size, endpoint=False)
        freq = 440.0
        chunk = 0.5 * np.sin(2 * np.pi * freq * t)

        # Feed it 3 times to fill history enough for variance
        for _ in range(3):
            metrics = self.sensor.analyze_chunk(chunk)

        # Pitch should be constant ~440, so variance ~0
        self.assertTrue(metrics['pitch_estimation'] > 400)
        self.assertAlmostEqual(metrics['pitch_variance'], 0.0, delta=5.0) # Small delta for FFT precision

        # RMS should be constant, so RMS variance ~0
        self.assertAlmostEqual(metrics['rms_variance'], 0.0, delta=0.01)

    def test_varying_tone_variance(self):
        # Feed varying tones
        freqs = [440, 550, 440, 600, 440]
        t = np.linspace(0, 1.0, self.sensor.chunk_size, endpoint=False)

        for f in freqs:
            chunk = 0.5 * np.sin(2 * np.pi * f * t)
            metrics = self.sensor.analyze_chunk(chunk)

        # Variance should be high
        self.assertTrue(metrics['pitch_variance'] > 10.0)

    def test_activity_bursts(self):
        # Simulate bursts: Quiet -> Loud -> Quiet -> Loud
        quiet = np.zeros(self.sensor.chunk_size)
        loud = 0.5 * np.ones(self.sensor.chunk_size) # High RMS

        sequence = [quiet, loud, quiet, loud, quiet]

        for chunk in sequence:
            metrics = self.sensor.analyze_chunk(chunk)

        # Should detect bursts
        # History: [0, 0.5, 0, 0.5, 0]
        # Mean RMS: 0.2, Threshold: 0.16
        # Above: [False, True, False, True, False]
        # Crossings (F->T): 2 (at index 1 and 3)
        # Note: np.diff returns array of size N-1

        # Debug info
        # rms_arr = np.array(self.sensor.rms_history)
        # threshold = np.mean(rms_arr) * 0.8
        # above = rms_arr > threshold
        # print(f"\nRMS History: {rms_arr}")
        # print(f"Threshold: {threshold}")
        # print(f"Above: {above}")

        self.assertTrue(metrics['activity_bursts'] >= 1)

if __name__ == '__main__':
    unittest.main()
