import unittest
from unittest.mock import MagicMock
import numpy as np
from core.logic_engine import LogicEngine
from core.state_engine import StateEngine

class TestStateEstimation(unittest.TestCase):
    def setUp(self):
        # Mocks
        self.mock_lmm = MagicMock()
        self.mock_logger = MagicMock()

        # Setup LogicEngine with mocks
        self.logic = LogicEngine(logger=self.mock_logger, lmm_interface=self.mock_lmm)
        # We need to manually replace state_engine to spy on it easily,
        # or we can just check logic.state_engine.get_state()

        # Ensure LogicEngine uses the StateEngine (it creates one in __init__)
        self.initial_state = self.logic.state_engine.get_state()

    def test_end_to_end_state_update(self):
        """
        Simulate sensor data -> LogicEngine -> LMM Interface -> State Engine update
        """

        # 1. Setup Mock LMM Response
        mock_response = {
            "state_estimation": {
                "arousal": 75,
                "overload": 20,
                "focus": 80,
                "energy": 60,
                "mood": 50
            },
            "visual_context": ["person_sitting"],
            "suggestion": None
        }
        self.mock_lmm.process_data.return_value = mock_response
        self.mock_lmm.get_intervention_suggestion.return_value = None

        # 2. Simulate Sensor Data inputs
        # Audio: Loud enough to trigger?
        # LogicEngine triggers LMM if audio > 0.5 OR video > 20 OR periodic.
        # Let's force a trigger via update() by making it time for a periodic check
        self.logic.lmm_call_interval = 0 # Immediate
        self.logic.min_lmm_interval = 0

        # Feed some dummy data so it has something to send
        self.logic.process_audio_data(np.zeros(1024))
        self.logic.process_video_data(np.zeros((100,100,3), dtype=np.uint8))

        # 3. Trigger Update
        self.logic.update()

        # Wait for async thread
        if self.logic.lmm_thread:
            self.logic.lmm_thread.join()

        # 4. Verify LMM was called
        self.mock_lmm.process_data.assert_called_once()

        # 5. Verify State Engine Updated
        new_state = self.logic.state_engine.get_state()

        # Since history is size 5 and initialized with default values:
        # Defaults: Arousal 50. History: [50, 50, 50, 50, 50]
        # New value: 75. History: [50, 50, 50, 50, 75]. Sum=275. Avg=55.

        self.assertEqual(new_state["arousal"], 55)

        # Let's verify that repeated updates move the needle
        for _ in range(5):
             self.logic.state_engine.update(mock_response)

        final_state = self.logic.state_engine.get_state()
        # After 5 updates of 75, history should be [75, 75, 75, 75, 75] -> Avg 75
        # Wait, we already did one update above (so history had one 75).
        # We added 5 more. So it's fully saturated.
        self.assertEqual(final_state["arousal"], 75)

    def test_lmm_input_format(self):
        """
        Verify that LogicEngine constructs the LMM payload correctly with new metrics.
        """
        # Inject known metrics
        self.logic.audio_analysis = {
            "rms": 0.6,
            "pitch_estimation": 150.0,
            "pitch_variance": 20.0,
            "activity_bursts": 5,
            "zcr": 0.1
        }
        self.logic.audio_level = 0.6

        self.logic.video_analysis = {
            "face_detected": True,
            "face_size_ratio": 0.2,
            "vertical_position": 0.4
        }
        self.logic.video_activity = 5.0

        # Mock last frames so prepare_lmm_data works
        self.logic.last_video_frame = np.zeros((10,10,3), dtype=np.uint8)
        self.logic.last_audio_chunk = np.zeros(10)

        # Create payload
        payload = self.logic._prepare_lmm_data(trigger_reason="test")

        context = payload["user_context"]
        metrics = context["sensor_metrics"]

        # Verify metrics passed through
        self.assertEqual(metrics["audio_analysis"]["pitch_estimation"], 150.0)
        self.assertEqual(metrics["video_analysis"]["face_size_ratio"], 0.2)

        # Note: LMMInterface.process_data is responsible for formatting this into string.
        # We verified that in reading code.

if __name__ == '__main__':
    unittest.main()
