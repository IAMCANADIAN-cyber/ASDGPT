import json
from typing import Dict, Any, Optional

class StateEngine:
    """
    Manages the 5-dimensional state of the user:
    1. Arousal (0-100)
    2. Overload (0-100)
    3. Focus (0-100)
    4. Energy (0-100)
    5. Mood (0-100)
    """

    def __init__(self, logger=None):
        self.logger = logger
        # Initialize state to neutral/baseline values
        self.state = {
            "arousal": 50,
            "overload": 0,
            "focus": 50,
            "energy": 80,
            "mood": 50
        }
        # Keep track of history? Maybe later.

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

        # Update state with validation
        for dim in self.state.keys():
            if dim in new_state_est:
                val = new_state_est[dim]
                # Ensure value is int and within bounds 0-100
                try:
                    val = int(val)
                    val = max(0, min(100, val))
                    self.state[dim] = val
                except (ValueError, TypeError):
                    if self.logger:
                        self.logger.log_warning(f"StateEngine: Invalid value for {dim}: {new_state_est[dim]}")

        if self.logger:
            self.logger.log_info(f"StateEngine: Updated state to {self.state}")

if __name__ == '__main__':
    # Simple test
    print("Testing StateEngine...")
    engine = StateEngine()
    print(f"Initial State: {engine.get_state()}")

    # Test Update
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
    print(f"Updated State: {engine.get_state()}")

    assert engine.get_state()["arousal"] == 60
    assert engine.get_state()["focus"] == 90

    # Test Partial Update
    mock_partial = {
        "state_estimation": {
            "energy": 50
        }
    }
    engine.update(mock_partial)
    print(f"Partial Update State: {engine.get_state()}")
    assert engine.get_state()["energy"] == 50
    assert engine.get_state()["arousal"] == 60 # Should remain unchanged

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
    assert engine.get_state()["overload"] == 100 # Should cap at 100

    print("StateEngine tests passed.")
