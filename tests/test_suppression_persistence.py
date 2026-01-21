import pytest
import time
import json
import os
import shutil
import unittest
from unittest.mock import MagicMock
from core.intervention_engine import InterventionEngine
import config

# Create a temporary test directory for user data
TEST_USER_DATA_DIR = "test_user_data"
TEST_SUPPRESSIONS_FILE = os.path.join(TEST_USER_DATA_DIR, "suppressions.json")

@pytest.fixture
def setup_test_env():
    # Setup
    os.makedirs(TEST_USER_DATA_DIR, exist_ok=True)

    # Patch config in core.intervention_engine to ensure it uses the test paths
    with unittest.mock.patch('core.intervention_engine.config.USER_DATA_DIR', TEST_USER_DATA_DIR), \
         unittest.mock.patch('core.intervention_engine.config.SUPPRESSIONS_FILE', TEST_SUPPRESSIONS_FILE):
        yield

    # Teardown
    if os.path.exists(TEST_USER_DATA_DIR):
        shutil.rmtree(TEST_USER_DATA_DIR)

def test_suppression_persistence(setup_test_env):
    """Test that suppressions are saved to disk and loaded back."""

    mock_logic = MagicMock()
    engine = InterventionEngine(mock_logic)

    # 1. Add a suppression
    engine.suppress_intervention("test_intervention", 60) # 60 minutes

    assert "test_intervention" in engine.suppressed_interventions
    assert os.path.exists(TEST_SUPPRESSIONS_FILE)

    # Verify file content
    with open(TEST_SUPPRESSIONS_FILE, 'r') as f:
        data = json.load(f)
        assert "test_intervention" in data
        assert data["test_intervention"] > time.time()

    # 2. Create a new engine instance to test loading
    engine2 = InterventionEngine(mock_logic)
    assert "test_intervention" in engine2.suppressed_interventions
    assert engine2.suppressed_interventions["test_intervention"] == engine.suppressed_interventions["test_intervention"]

def test_expired_suppression_cleanup(setup_test_env):
    """Test that expired suppressions are removed on load."""

    # Manually create a file with an expired suppression
    expired_time = time.time() - 100
    data = {"expired_intervention": expired_time, "valid_intervention": time.time() + 3600}

    os.makedirs(TEST_USER_DATA_DIR, exist_ok=True)
    with open(TEST_SUPPRESSIONS_FILE, 'w') as f:
        json.dump(data, f)

    mock_logic = MagicMock()
    engine = InterventionEngine(mock_logic)

    assert "expired_intervention" not in engine.suppressed_interventions
    assert "valid_intervention" in engine.suppressed_interventions

    # Verify file was updated (expired removed)
    with open(TEST_SUPPRESSIONS_FILE, 'r') as f:
        data_loaded = json.load(f)
        assert "expired_intervention" not in data_loaded
