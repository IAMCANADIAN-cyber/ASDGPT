import json
from typing import Dict, Any, Optional
from collections import deque

class StateEngine:
    """
    Manages the 5-dimensional state of the user:
    1. Arousal (0-100)
    2. Overload (0-100)
    3. Focus (0-100)
    4. Energy (0-100)
    5. Mood (0-100)
    """

    def __init__(self, logger=None, history_size: int = 5):
        self.logger = logger
        self.history_size = history_size

        # Initialize state to neutral/baseline values
        self.state = {
            "arousal": 50,
            "overload": 0,
            "focus": 50,
            "energy": 80,
            "mood": 50
        }

        # Initialize history for each dimension with the initial value
        # This prevents the state from starting at 0 if we were to start with empty history
        self.history = {
            dim: deque([val] * history_size, maxlen=history_size)
            for dim, val in self.state.items()
        }

    def get_state(self) -> Dict[str, int]:
        """Returns the current state."""
        return self.state.copy()

    def update(self, lmm_analysis: Optional[Dict[str, Any]]) -> None:
        """
        Updates the state based on LMM analysis.
        Expects lmm_analysis to contain a "state_estimation" key with the 5 dimensions.
        """
        if not lmm_analysis:
            return

        new_state_est = lmm_analysis.get("state_estimation")
        if not new_state_est:
            if self.logger:
                self.logger.log_debug("StateEngine: No 'state_estimation' found in LMM analysis.")
            return

        # Update state with validation and smoothing
        for dim in self.state.keys():
            if dim in new_state_est:
                raw_val = new_state_est[dim]
                # Ensure value is int and within bounds 0-100
                try:
                    val = int(raw_val)
                    val = max(0, min(100, val))

                    # Add to history
                    self.history[dim].append(val)

                    # Calculate smoothed value (simple moving average)
                    smoothed_val = int(sum(self.history[dim]) / len(self.history[dim]))
                    self.state[dim] = smoothed_val

                except (ValueError, TypeError):
                    if self.logger:
                        self.logger.log_warning(f"StateEngine: Invalid value for {dim}: {new_state_est[dim]}")

        if self.logger:
            self.logger.log_info(f"StateEngine: Updated state to {self.state}")

if __name__ == '__main__':
    # Simple test
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
