import pytest
import time
import json
import os
import shutil
from unittest.mock import MagicMock
from core.intervention_engine import InterventionEngine
import config

# Create a temporary test directory for user data
TEST_USER_DATA_DIR = "test_feedback_loop_data_v2"
TEST_SUPPRESSIONS_FILE = os.path.join(TEST_USER_DATA_DIR, "suppressions.json")
TEST_PREFERENCES_FILE = os.path.join(TEST_USER_DATA_DIR, "preferences.json")

@pytest.fixture
def setup_test_env():
    # Setup
    os.makedirs(TEST_USER_DATA_DIR, exist_ok=True)
    # Override config paths for testing

    # Store original config values
    orig_user_data_dir = getattr(config, 'USER_DATA_DIR', "user_data")
    orig_suppressions_file = getattr(config, 'SUPPRESSIONS_FILE', "user_data/suppressions.json")
    orig_preferences_file = getattr(config, 'PREFERENCES_FILE', "user_data/preferences.json")
    orig_suppression_minutes = getattr(config, 'FEEDBACK_SUPPRESSION_MINUTES', 240)
    orig_feedback_window = getattr(config, 'FEEDBACK_WINDOW_SECONDS', 15)

    config.USER_DATA_DIR = TEST_USER_DATA_DIR
    config.SUPPRESSIONS_FILE = TEST_SUPPRESSIONS_FILE
    config.PREFERENCES_FILE = TEST_PREFERENCES_FILE
    config.FEEDBACK_SUPPRESSION_MINUTES = 240 # Default 4 hours
    config.FEEDBACK_WINDOW_SECONDS = 5

    yield

    # Teardown
    if os.path.exists(TEST_USER_DATA_DIR):
        shutil.rmtree(TEST_USER_DATA_DIR)

    # Restore original config
    config.USER_DATA_DIR = orig_user_data_dir
    config.SUPPRESSIONS_FILE = orig_suppressions_file
    config.PREFERENCES_FILE = orig_preferences_file
    config.FEEDBACK_SUPPRESSION_MINUTES = orig_suppression_minutes
    config.FEEDBACK_WINDOW_SECONDS = orig_feedback_window

def test_feedback_unhelpful_suppression(setup_test_env):
    """Test that 'unhelpful' feedback suppresses the intervention type for the configured duration."""

    mock_logic = MagicMock()
    mock_logic.get_mode.return_value = "active"
    engine = InterventionEngine(mock_logic)

    # 1. Start an intervention
    details = {"type": "posture_alert", "message": "Sit up."}
    engine.start_intervention(details)

    # Mock that it finished immediately so we can provide feedback
    time.sleep(0.1) # Wait for thread to start
    engine.stop_intervention() # Stop it

    # Wait for the intervention thread to cleanup and store the intervention
    # stop_intervention kills the subprocess, but the thread needs to finish execution
    max_retries = 10
    for _ in range(max_retries):
        if engine.last_feedback_eligible_intervention["type"] == "posture_alert":
            break
        time.sleep(0.1)

    assert engine.last_feedback_eligible_intervention["type"] == "posture_alert"

    # 2. Register "unhelpful" feedback
    engine.register_feedback("unhelpful")

    # 3. Check suppression
    assert "posture_alert" in engine.suppressed_interventions
    expiry = engine.suppressed_interventions["posture_alert"]

    # Should be approx 4 hours from now
    expected_expiry = time.time() + (240 * 60)
    assert abs(expiry - expected_expiry) < 10 # 10 seconds tolerance

    # 4. Verify persistence
    assert os.path.exists(TEST_SUPPRESSIONS_FILE)
    with open(TEST_SUPPRESSIONS_FILE, 'r') as f:
        data = json.load(f)
        assert "posture_alert" in data

    # 5. Try to start it again (should fail)
    result = engine.start_intervention(details)
    assert result is False

def test_feedback_helpful_preference(setup_test_env):
    """Test that 'helpful' feedback tracks preference."""

    mock_logic = MagicMock()
    mock_logic.get_mode.return_value = "active"
    engine = InterventionEngine(mock_logic)

    details = {"type": "deep_breath", "message": "Breathe."}
    engine.start_intervention(details)
    time.sleep(0.1)
    engine.stop_intervention()

    # Wait for state update
    max_retries = 10
    for _ in range(max_retries):
        if engine.last_feedback_eligible_intervention["type"] == "deep_breath":
            break
        time.sleep(0.1)

    engine.register_feedback("helpful")

    assert "deep_breath" in engine.preferred_interventions
    assert engine.preferred_interventions["deep_breath"]["count"] == 1

    # Verify persistence
    assert os.path.exists(TEST_PREFERENCES_FILE)

    # Do it again
    # Reset last_intervention_time to bypass rate limit
    engine.last_intervention_time = 0
    engine.start_intervention(details)
    time.sleep(0.1)
    engine.stop_intervention()

    # Wait for state update
    for _ in range(max_retries):
        if engine.last_feedback_eligible_intervention["type"] == "deep_breath":
            break
        time.sleep(0.1)

    engine.register_feedback("helpful")

    assert engine.preferred_interventions["deep_breath"]["count"] == 2

def test_feedback_window_expiry(setup_test_env):
    """Test that feedback is rejected if too much time has passed."""

    mock_logic = MagicMock()
    mock_logic.get_mode.return_value = "active"
    engine = InterventionEngine(mock_logic)

    details = {"type": "test_expiry", "message": "Test"}
    engine.start_intervention(details)
    time.sleep(0.1)
    engine.stop_intervention()

    # Wait for state update
    max_retries = 10
    for _ in range(max_retries):
        if engine.last_feedback_eligible_intervention["type"] == "test_expiry":
            break
        time.sleep(0.1)

    # Manually tamper with the timestamp to make it old
    engine.last_feedback_eligible_intervention["timestamp"] = time.time() - 100

    # Register feedback
    engine.register_feedback("helpful")

    # Should NOT be counted
    assert "test_expiry" not in engine.preferred_interventions

def test_load_suppressions_on_init(setup_test_env):
    """Test that suppressions are loaded when engine starts."""

    # Pre-populate file
    data = {"loaded_intervention": time.time() + 3600}
    with open(TEST_SUPPRESSIONS_FILE, 'w') as f:
        json.dump(data, f)

    mock_logic = MagicMock()
    engine = InterventionEngine(mock_logic)

    assert "loaded_intervention" in engine.suppressed_interventions

def test_get_preferred_interventions_sorted(setup_test_env):
    """Test that get_preferred_intervention_types returns sorted list."""

    mock_logic = MagicMock()
    engine = InterventionEngine(mock_logic)

    # Manually populate
    engine.preferred_interventions = {
        "ok_intervention": {"count": 1},
        "best_intervention": {"count": 10},
        "good_intervention": {"count": 5}
    }

    prefs = engine.get_preferred_intervention_types()
    assert prefs == ["best_intervention", "good_intervention", "ok_intervention"]
