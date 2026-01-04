import pytest
from core.state_engine import StateEngine
from collections import deque

class MockLogger:
    def __init__(self):
        self.logs = []

    def log_info(self, msg):
        self.logs.append(("INFO", msg))

    def log_warning(self, msg):
        self.logs.append(("WARN", msg))

    def log_debug(self, msg):
        self.logs.append(("DEBUG", msg))

def test_state_engine_initialization():
    engine = StateEngine()
    state = engine.get_state()
    assert state["arousal"] == 50
    assert state["overload"] == 0
    assert state["focus"] == 50
    assert state["energy"] == 80
    assert state["mood"] == 50
    assert len(engine.history["arousal"]) == 5

def test_state_update_smoothing():
    engine = StateEngine(history_size=3)
    # Initial state is 50. History: [50, 50, 50]

    # Update with 80
    engine.update({"state_estimation": {"arousal": 80}})
    # History: [50, 50, 80] -> Avg: 60
    assert engine.get_state()["arousal"] == 60

    # Update with 80 again
    engine.update({"state_estimation": {"arousal": 80}})
    # History: [50, 80, 80] -> Avg: 70
    assert engine.get_state()["arousal"] == 70

    # Update with 80 again
    engine.update({"state_estimation": {"arousal": 80}})
    # History: [80, 80, 80] -> Avg: 80
    assert engine.get_state()["arousal"] == 80

def test_state_update_invalid_input():
    logger = MockLogger()
    engine = StateEngine(logger=logger)

    # Update with string that can't be parsed
    engine.update({"state_estimation": {"arousal": "high"}})

    # State should not change
    assert engine.get_state()["arousal"] == 50

    # Should log warning
    warnings = [log for lvl, log in logger.logs if lvl == "WARN"]
    assert any("Invalid value" in msg for msg in warnings)

def test_state_update_bounds_clamping():
    engine = StateEngine(history_size=1) # History 1 for immediate effect

    engine.update({"state_estimation": {"overload": 150}})
    assert engine.get_state()["overload"] == 100

    engine.update({"state_estimation": {"overload": -50}})
    assert engine.get_state()["overload"] == 0

def test_missing_keys_ignored():
    engine = StateEngine(history_size=1)

    # Update only one dimension
    engine.update({"state_estimation": {"focus": 90}})

    state = engine.get_state()
    assert state["focus"] == 90
    assert state["arousal"] == 50 # Unchanged
