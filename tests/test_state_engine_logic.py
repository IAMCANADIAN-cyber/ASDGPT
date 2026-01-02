import pytest
from core.state_engine import StateEngine

class TestStateEngineLogic:
    def test_state_engine_update_logic(self):
        print("Testing StateEngine...")
        engine = StateEngine(history_size=5) # Ensure history size is set
        print(f"Initial State: {engine.get_state()}")

        # Test Update
        # Initial state is 50/0/50/80/50
        # Input: Arousal 60. History becomes [50, 50, 50, 50, 60]. Avg = 52.
        mock_lmm_output = {
            "state_estimation": {
                "arousal": 60,
                "overload": 10,
                "focus": 90,
                "energy": 70,
                "mood": 60
            },
            "suggestion": "Keep going!"
        }
        engine.update(mock_lmm_output)
        print(f"Updated State (smoothed): {engine.get_state()}")

        # Check Arousal: (50*4 + 60)/5 = 260/5 = 52
        assert engine.get_state()["arousal"] == 52, f"Expected 52, got {engine.get_state()['arousal']}"

        # Test Convergence
        # If we keep sending 60, it should eventually reach 60
        for _ in range(5):
            engine.update(mock_lmm_output)

        print(f"Converged State: {engine.get_state()}")
        assert engine.get_state()["arousal"] == 60
        assert engine.get_state()["focus"] == 90 # Initial was 50. (50*4+90)/5=58... eventually 90

        # Test Partial Update
        mock_partial = {
            "state_estimation": {
                "energy": 50
            }
        }
        # Current energy converged to 70 (initial 80 -> 70 from previous mock)
        # Actually wait, mock_lmm_output had energy 70.
        # So history for energy is [70, 70, 70, 70, 70].
        # Update with 50 -> [70, 70, 70, 70, 50] -> avg 66
        engine.update(mock_partial)
        print(f"Partial Update State: {engine.get_state()}")
        assert engine.get_state()["energy"] == 66
        # Arousal should remain 60 (history [60,60,60,60,60])
        assert engine.get_state()["arousal"] == 60

        # Test Invalid Data
        mock_invalid = {
            "state_estimation": {
                "mood": "happy", # Not an int
                "overload": 150  # Out of bounds
            }
        }
        engine.update(mock_invalid)
        print(f"Invalid Update State: {engine.get_state()}")
        assert engine.get_state()["mood"] == 60 # Should not change
        # Overload was 0 -> [0,0,0,0,0]. Update 10 from mock_lmm_output x 6 times?
        # Wait, in the loop above we updated 5 times with mock_lmm_output (overload 10).
        # So overload history is [10, 10, 10, 10, 10].
        # Invalid update attempts 150 -> caps at 100.
        # History becomes [10, 10, 10, 10, 100]. Avg = 140/5 = 28.
        assert engine.get_state()["overload"] == 28

        print("StateEngine tests passed.")
