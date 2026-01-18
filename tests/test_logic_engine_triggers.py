import unittest
from unittest.mock import MagicMock, patch
import time
import numpy as np
import config
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface
from core.intervention_engine import InterventionEngine

class TestLogicEngineTriggers(unittest.TestCase):
    def setUp(self):
        # Mock LMM Interface
        self.mock_lmm = MagicMock(spec=LMMInterface)
        self.mock_lmm.process_data = MagicMock()
        self.mock_lmm.get_intervention_suggestion = MagicMock(return_value=None)

        # Capture context passed to LMM
        self.captured_payload = None
        def side_effect(video_data=None, audio_data=None, user_context=None):
            self.captured_payload = {
                "user_context": user_context,
                "video_data": video_data,
                "audio_data": audio_data
            }
            return {
                "state_estimation": {"arousal": 50, "overload": 10, "focus": 60, "energy": 75, "mood": 55},
                "suggestion": None
            }
        self.mock_lmm.process_data.side_effect = side_effect

        # Mock Intervention Engine
        self.mock_intervention = MagicMock(spec=InterventionEngine)

        # Mock Sensors (optional, as we can inject data directly into logic engine methods)
        self.mock_audio_sensor = MagicMock()
        self.mock_audio_sensor.analyze_chunk.return_value = {"rms": 0.0, "is_speech": False}

        self.mock_video_sensor = MagicMock()
        self.mock_video_sensor.process_frame.return_value = {"video_activity": 0.0, "face_detected": False, "face_count": 0}

        # Initialize Logic Engine
        self.logic_engine = LogicEngine(
            audio_sensor=self.mock_audio_sensor,
            video_sensor=self.mock_video_sensor,
            lmm_interface=self.mock_lmm
        )
        self.logic_engine.set_intervention_engine(self.mock_intervention)

        # Configure Logic Engine for fast testing
        self.logic_engine.lmm_call_interval = 2
        self.logic_engine.min_lmm_interval = 0 # Allow immediate calls
        self.logic_engine.audio_threshold_high = 0.5
        self.logic_engine.video_activity_threshold_high = 10.0

    def tearDown(self):
        if self.logic_engine.lmm_thread and self.logic_engine.lmm_thread.is_alive():
            self.logic_engine.lmm_thread.join(timeout=2)

    def test_periodic_check(self):
        """Test that update triggers LMM periodically when interval expires."""
        print("\nTest: Periodic Check")
        # Ensure no call initially
        self.logic_engine.last_lmm_call_time = time.time()
        self.logic_engine.update()
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        self.assertIsNone(self.captured_payload, "Should not trigger immediately after reset")

        # Advance time implicitly by resetting last_call_time to past
        self.logic_engine.last_lmm_call_time = time.time() - 5

        # Inject some dummy data so it has something to send
        self.logic_engine.last_video_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.logic_engine.last_audio_chunk = np.zeros(1024)

        self.logic_engine.update()
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        self.assertIsNotNone(self.captured_payload)
        self.assertEqual(self.captured_payload["user_context"]["trigger_reason"], "periodic_check")

    def test_high_audio_trigger(self):
        """Test that high audio level triggers LMM analysis."""
        print("\nTest: High Audio Trigger")
        # Reset timer so periodic doesn't fire
        self.logic_engine.last_lmm_call_time = time.time()

        # Simulate High Audio + Speech
        # LogicEngine uses sensor.analyze_chunk results.
        self.mock_audio_sensor.analyze_chunk.return_value = {
            "rms": 0.8,
            "is_speech": True,
            "speech_confidence": 0.9
        }

        # Process data
        chunk = np.ones(1024) # dummy data
        self.logic_engine.process_audio_data(chunk)

        # Also need video frame to send data
        self.logic_engine.last_video_frame = np.zeros((100, 100, 3), dtype=np.uint8)

        self.logic_engine.update()
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        self.assertIsNotNone(self.captured_payload)
        self.assertEqual(self.captured_payload["user_context"]["trigger_reason"], "high_audio_level")
        self.assertGreater(self.captured_payload["user_context"]["sensor_metrics"]["audio_level"], 0.5)

    def test_high_audio_ignored_if_not_speech(self):
        """Test that high audio level is ignored if not identified as speech."""
        print("\nTest: High Audio Ignored (No Speech)")
        self.logic_engine.last_lmm_call_time = time.time()

        self.mock_audio_sensor.analyze_chunk.return_value = {
            "rms": 0.8,
            "is_speech": False
        }

        chunk = np.ones(1024)
        self.logic_engine.process_audio_data(chunk)
        self.logic_engine.last_video_frame = np.zeros((100, 100, 3), dtype=np.uint8)

        self.logic_engine.update()
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        self.assertIsNone(self.captured_payload)

    def test_high_video_activity_trigger(self):
        """Test that high video activity with face triggers LMM analysis."""
        print("\nTest: High Video Activity Trigger")
        self.logic_engine.last_lmm_call_time = time.time()

        # Reset audio to silence
        self.mock_audio_sensor.analyze_chunk.return_value = {"rms": 0.0, "is_speech": False}
        self.logic_engine.process_audio_data(np.zeros(1024))

        # Simulate High Activity + Face
        self.mock_video_sensor.process_frame.return_value = {
            "video_activity": 20.0,
            "face_detected": True,
            "face_count": 1
        }

        frame = np.ones((100, 100, 3), dtype=np.uint8)
        self.logic_engine.process_video_data(frame)

        self.logic_engine.update()
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        self.assertIsNotNone(self.captured_payload)
        self.assertEqual(self.captured_payload["user_context"]["trigger_reason"], "high_video_activity")
        self.assertGreater(self.captured_payload["user_context"]["sensor_metrics"]["video_activity"], 10.0)

    def test_high_video_activity_ignored_no_face(self):
        """Test that high video activity is ignored if no face is detected."""
        print("\nTest: High Video Activity Ignored (No Face)")
        self.logic_engine.last_lmm_call_time = time.time()

        self.mock_video_sensor.process_frame.return_value = {
            "video_activity": 20.0,
            "face_detected": False,
            "face_count": 0
        }

        frame = np.ones((100, 100, 3), dtype=np.uint8)
        self.logic_engine.process_video_data(frame)

        self.logic_engine.update()
        if self.logic_engine.lmm_thread: self.logic_engine.lmm_thread.join()

        self.assertIsNone(self.captured_payload)

if __name__ == '__main__':
    unittest.main()
