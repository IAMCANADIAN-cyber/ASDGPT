import json
import threading
from typing import Dict, Any, Optional
from collections import deque
import config

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
        self._lock = threading.Lock()

        # Initialize state to neutral/baseline values from config
        default_baseline = {
            "arousal": 50,
            "overload": 0,
            "focus": 50,
            "energy": 80,
            "mood": 50
        }

        baseline = getattr(config, 'BASELINE_STATE', default_baseline)

        # Ensure all keys exist in baseline, fall back to default if missing
        self.state = {}
        for key, val in default_baseline.items():
            self.state[key] = baseline.get(key, val)

        # Initialize history for each dimension with the initial value
        # This prevents the state from starting at 0 if we were to start with empty history
        self.history = {
            dim: deque([val] * history_size, maxlen=history_size)
            for dim, val in self.state.items()
        }

    def get_state(self) -> Dict[str, int]:
        """Returns the current state."""
        with self._lock:
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

        with self._lock:
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
