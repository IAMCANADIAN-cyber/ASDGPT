import unittest
import time
import sys
import os
import threading
import numpy as np

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.logic_engine import LogicEngine
from core.data_logger import DataLogger
import config

class TestSignalQualityIntegration(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.logger = DataLogger("test_signal_quality.log")

        class MockLMMInterface:
            def __init__(self):
                self.triggered = False
                self.last_reason = None

            def process_data(self, video_data=None, audio_data=None, user_context=None):
                self.triggered = True
                self.last_reason = user_context.get("trigger_reason")
                return {"state_estimation": {}, "suggestion": None}

            def get_intervention_suggestion(self, analysis):
                return None

        self.mock_lmm = MockLMMInterface()

        # Initialize LogicEngine with mocks
        self.logic_engine = LogicEngine(logger=self.logger, lmm_interface=self.mock_lmm)
        self.logic_engine.audio_sensor = None # We will inject data manually
        self.logic_engine.video_sensor = None

        # Settings for testing
        self.logic_engine.audio_threshold_high = 0.5
        self.logic_engine.video_activity_threshold_high = 10.0
        self.logic_engine.min_lmm_interval = 0 # Allow immediate triggers
        self.logic_engine.lmm_call_interval = 999 # Disable periodic for this test

        # Prepare valid data so _prepare_lmm_data doesn't return None
        self.logic_engine.last_video_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.logic_engine.last_audio_chunk = np.zeros(1024)


    def _wait_for_lmm(self):
        # Wait for the async LMM thread to finish
        if self.logic_engine.lmm_thread and self.logic_engine.lmm_thread.is_alive():
            self.logic_engine.lmm_thread.join(timeout=2.0)

    def test_audio_noise_suppression(self):
        """Test that loud non-speech noise does NOT trigger the LMM."""
        print("\n--- Test: Audio Noise Suppression ---")

        # 1. Simulate Loud Noise (High RMS, is_speech=False)
        self.logic_engine.audio_level = 0.8
        self.logic_engine.audio_analysis = {
            "rms": 0.8,
            "is_speech": False, # Crucial: Noise, not speech
            "speech_confidence": 0.1
        }

        # Reset trigger state and ensure no periodic trigger
        self.mock_lmm.triggered = False
        self.logic_engine.last_lmm_call_time = time.time()

        # Run Update
        self.logic_engine.update()
        self._wait_for_lmm()

        if self.mock_lmm.triggered:
             print(f"LMM triggered with reason: {self.mock_lmm.last_reason}")

        self.assertFalse(self.mock_lmm.triggered, "Loud noise (is_speech=False) should NOT trigger LMM")

    def test_audio_speech_trigger(self):
        """Test that loud speech DOES trigger the LMM."""
        print("\n--- Test: Audio Speech Trigger ---")

        # 2. Simulate Loud Speech (High RMS, is_speech=True)
        self.logic_engine.audio_level = 0.8
        self.logic_engine.audio_analysis = {
            "rms": 0.8,
            "is_speech": True,
            "speech_confidence": 0.8
        }

        # Reset trigger state
        self.mock_lmm.triggered = False
        self.logic_engine.last_lmm_call_time = time.time()

        # Run Update
        self.logic_engine.update()
        self._wait_for_lmm()

        self.assertTrue(self.mock_lmm.triggered, "Loud speech (is_speech=True) SHOULD trigger LMM")
        self.assertEqual(self.mock_lmm.last_reason, "high_audio_level")

    def test_video_ghost_suppression(self):
        """Test that high video activity without a face does NOT trigger the LMM."""
        print("\n--- Test: Video Ghost Suppression ---")

        # 3. Simulate High Activity, No Face (e.g. cat, shadows)
        self.logic_engine.video_activity = 20.0
        self.logic_engine.face_metrics = {
            "face_detected": False,
            "face_count": 0
        }

        # Reset trigger state
        self.mock_lmm.triggered = False
        self.logic_engine.last_lmm_call_time = time.time()

        # Run Update
        self.logic_engine.update()
        self._wait_for_lmm()

        self.assertFalse(self.mock_lmm.triggered, "High activity without face should NOT trigger LMM")

    def test_video_user_activity_trigger(self):
        """Test that high video activity WITH a face DOES trigger the LMM."""
        print("\n--- Test: Video User Activity Trigger ---")

        # 4. Simulate High Activity, User Present
        self.logic_engine.video_activity = 20.0
        self.logic_engine.face_metrics = {
            "face_detected": True,
            "face_count": 1
        }

        # Reset trigger state
        self.mock_lmm.triggered = False
        self.logic_engine.last_lmm_call_time = time.time()

        # Run Update
        self.logic_engine.update()
        self._wait_for_lmm()

        self.assertTrue(self.mock_lmm.triggered, "High activity with face SHOULD trigger LMM")
        self.assertEqual(self.mock_lmm.last_reason, "high_video_activity")

if __name__ == '__main__':
    unittest.main()
