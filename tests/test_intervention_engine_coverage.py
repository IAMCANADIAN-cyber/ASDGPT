import pytest
import threading
import time
import os
import shutil
import json
import subprocess
import platform
from unittest.mock import MagicMock, patch
from core.intervention_engine import InterventionEngine

class MockLogicEngine:
    def __init__(self):
        self.mode = "active"
        self.last_video_frame = None

    def get_mode(self):
        return self.mode

    def set_mode(self, mode):
        self.mode = mode

class MockApp:
    def __init__(self):
        self.data_logger = MagicMock()
        self.tray_icon = MagicMock()

@pytest.fixture
def temp_config_paths(tmp_path):
    suppressions_file = tmp_path / "suppressions.json"
    preferences_file = tmp_path / "preferences.json"

    with patch('config.SUPPRESSIONS_FILE', str(suppressions_file)), \
         patch('config.PREFERENCES_FILE', str(preferences_file)):
        yield suppressions_file, preferences_file

@pytest.fixture
def intervention_engine(temp_config_paths):
    # Patch the rate limit to 0 for all tests by default to avoid timing issues
    with patch('config.MIN_TIME_BETWEEN_INTERVENTIONS', 0):
        logic_engine = MockLogicEngine()
        app = MockApp()
        engine = InterventionEngine(logic_engine, app)
        # Ensure no residual state
        engine.last_intervention_time = 0
        yield engine

def test_initialization(intervention_engine):
    assert intervention_engine.logic_engine is not None
    assert intervention_engine.app is not None
    assert isinstance(intervention_engine.suppressed_interventions, dict)
    assert isinstance(intervention_engine.preferred_interventions, dict)

def test_start_intervention_missing_id_and_type(intervention_engine):
    result = intervention_engine.start_intervention({})
    assert result is False
    intervention_engine.app.data_logger.log_warning.assert_called()

def test_start_intervention_valid_id(intervention_engine):
    # Mocking wait and speak to avoid actual delays/system calls
    # We use a longer wait in logic to ensure thread stays alive for assertion
    with patch.object(intervention_engine, '_speak') as mock_speak, \
         patch.object(intervention_engine, '_wait') as mock_wait:

        # Make _wait hang a bit so we can check is_set()
        def slow_wait(duration):
            time.sleep(0.5)
        mock_wait.side_effect = slow_wait

        details = {"id": "shoulder_drop"} # Has a sequence with wait
        result = intervention_engine.start_intervention(details)
        assert result is True

        # Give thread time to start and enter wait
        time.sleep(0.1)

        assert intervention_engine._intervention_active.is_set()
        intervention_engine.stop_intervention()

def test_start_intervention_ad_hoc(intervention_engine):
    with patch.object(intervention_engine, '_speak') as mock_speak:
        # Use a unique type to avoid potential collisions with other tests if state persists
        details = {"type": "ad_hoc_type", "message": "Test message"}
        result = intervention_engine.start_intervention(details)
        assert result is True

        time.sleep(0.1)
        intervention_engine.stop_intervention()

        # Verify speak was called
        mock_speak.assert_called_with("Test message", blocking=True)

def test_suppression_logic(intervention_engine, temp_config_paths):
    # Suppress an intervention
    intervention_engine.suppress_intervention("test_type_suppressed", 10)
    assert "test_type_suppressed" in intervention_engine.suppressed_interventions

    # Attempt to start it
    details = {"type": "test_type_suppressed", "message": "Test message"}
    result = intervention_engine.start_intervention(details)
    assert result is False

def test_mode_suppression(intervention_engine):
    intervention_engine.logic_engine.set_mode("paused")
    details = {"type": "test_type", "message": "Test message"}
    result = intervention_engine.start_intervention(details)
    assert result is False

def test_rate_limiting(intervention_engine):
    # We need to explicitly patch it to > 0 here to test rate limiting
    with patch('config.MIN_TIME_BETWEEN_INTERVENTIONS', 10):
        # First one succeeds
        with patch.object(intervention_engine, '_speak'):
            assert intervention_engine.start_intervention({"type": "t1", "message": "m1"}) is True

            # Second one fails (too soon)
            assert intervention_engine.start_intervention({"type": "t2", "message": "m2"}) is False

def test_preemption_logic(intervention_engine):
    with patch.object(intervention_engine, '_speak') as mock_speak, \
         patch.object(intervention_engine, '_wait') as mock_wait:

        # We need the first intervention to stay active.
        # Ad-hoc interventions call _speak(blocking=True).
        # We mock _speak to simulate blocking but respecting the active flag

        def blocking_speak(text, blocking=True):
                # Simulate long speech but check for cancellation
                 start = time.time()
                 while time.time() - start < 2:
                     if not intervention_engine._intervention_active.is_set():
                         break
                     time.sleep(0.1)

        mock_speak.side_effect = blocking_speak

        # Start low tier intervention
        details_low = {"type": "low", "message": "low", "tier": 1}
        assert intervention_engine.start_intervention(details_low) is True

        time.sleep(0.1) # Ensure it's active
        assert intervention_engine._intervention_active.is_set()

        # Reset time just in case, though patch should handle it
        intervention_engine.last_intervention_time = 0

        # Start high tier intervention (should preempt)
        details_high = {"type": "high", "message": "high", "tier": 3}
        assert intervention_engine.start_intervention(details_high) is True

        # Give it a moment to switch and start "speaking" high
        time.sleep(0.1)

        # Current details should reflect high tier
        assert intervention_engine._current_intervention_details["type"] == "high"

        intervention_engine.stop_intervention()

def test_lower_priority_ignored(intervention_engine):
    with patch.object(intervention_engine, '_speak') as mock_speak:

        def blocking_speak(text, blocking=True):
            if blocking and text == "high":
                 start = time.time()
                 while time.time() - start < 2:
                     if not intervention_engine._intervention_active.is_set():
                         break
                     time.sleep(0.1)
        mock_speak.side_effect = blocking_speak

        # Start high tier intervention
        details_high = {"type": "high", "message": "high", "tier": 3}
        assert intervention_engine.start_intervention(details_high) is True

        time.sleep(0.1)

        # Start low tier intervention (should be ignored)
        details_low = {"type": "low", "message": "low", "tier": 1}
        assert intervention_engine.start_intervention(details_low) is False

        # Current details should still be high tier
        assert intervention_engine._current_intervention_details["type"] == "high"

        intervention_engine.stop_intervention()

def test_feedback_registration(intervention_engine):
    # Setup a feedback eligible intervention
    intervention_engine._store_last_intervention("test_msg", "test_type_feedback")

    # Register feedback
    intervention_engine.register_feedback("Helpful")

    # Verify logger was called with event
    intervention_engine.app.data_logger.log_event.assert_called()
    call_args = intervention_engine.app.data_logger.log_event.call_args
    assert call_args[1]["event_type"] == "user_feedback"
    assert call_args[1]["payload"]["feedback_value"] == "Helpful"

def test_feedback_suppression(intervention_engine):
    # Setup eligible
    intervention_engine._store_last_intervention("test_msg", "test_type_feedback_suppressed")

    # Register negative feedback
    intervention_engine.register_feedback("Unhelpful")

    # Verify it was suppressed
    assert "test_type_feedback_suppressed" in intervention_engine.suppressed_interventions

def test_tts_linux_fallback(intervention_engine):
    """Test TTS fallback logic specifically."""
    # We patch platform.system global and subprocess.Popen in the module
    with patch('platform.system', return_value='Linux') as mock_system, \
         patch('core.intervention_engine.subprocess.Popen') as mock_popen:

        # First call raises FileNotFoundError (simulating espeak missing)
        # Second call returns a mock process (simulating spd-say working)
        mock_popen.side_effect = [FileNotFoundError, MagicMock()]

        # IMPORTANT: _speak checks if intervention is active before speaking if blocking=True
        intervention_engine._intervention_active.set()

        intervention_engine._speak("test text")

        assert mock_popen.call_count == 2
        # Check args of the second call
        args, _ = mock_popen.call_args_list[1]
        assert args[0] == ["spd-say", "test text"]

def test_sound_file_missing(intervention_engine):
    with patch('os.path.exists', return_value=False):
        intervention_engine._play_sound("missing.wav")
        intervention_engine.app.data_logger.log_warning.assert_called()

def test_image_display_no_pil(intervention_engine):
    # Simulate PIL missing
    with patch('core.intervention_engine.Image', None):
        intervention_engine._show_visual_prompt("test.jpg")
        intervention_engine.app.data_logger.log_warning.assert_called_with("PIL (Pillow) library not available. Cannot show image.")

def test_record_video_no_cv2(intervention_engine):
    # Simulate cv2 missing
    with patch('core.intervention_engine.cv2', None):
        intervention_engine._record_video("test")
        intervention_engine.app.data_logger.log_warning.assert_called()
