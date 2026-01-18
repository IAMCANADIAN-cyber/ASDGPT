import pytest
import time
import json
import os
import shutil
from unittest.mock import MagicMock, patch, call
from core.intervention_engine import InterventionEngine
import config

TEST_USER_DATA_DIR = "test_coverage_data"
TEST_SUPPRESSIONS_FILE = os.path.join(TEST_USER_DATA_DIR, "suppressions.json")
TEST_PREFERENCES_FILE = os.path.join(TEST_USER_DATA_DIR, "preferences.json")

@pytest.fixture
def setup_coverage_env():
    os.makedirs(TEST_USER_DATA_DIR, exist_ok=True)

    orig_user_data_dir = getattr(config, 'USER_DATA_DIR', "user_data")
    orig_suppressions_file = getattr(config, 'SUPPRESSIONS_FILE', "user_data/suppressions.json")
    orig_preferences_file = getattr(config, 'PREFERENCES_FILE', "user_data/preferences.json")

    config.USER_DATA_DIR = TEST_USER_DATA_DIR
    config.SUPPRESSIONS_FILE = TEST_SUPPRESSIONS_FILE
    config.PREFERENCES_FILE = TEST_PREFERENCES_FILE

    yield

    if os.path.exists(TEST_USER_DATA_DIR):
        shutil.rmtree(TEST_USER_DATA_DIR)

    config.USER_DATA_DIR = orig_user_data_dir
    config.SUPPRESSIONS_FILE = orig_suppressions_file
    config.PREFERENCES_FILE = orig_preferences_file

def test_load_suppressions_error(setup_coverage_env):
    """Test error handling when loading suppressions fails."""
    mock_logic = MagicMock()
    mock_app = MagicMock()
    engine = InterventionEngine(mock_logic, mock_app)

    # Mock open to raise exception
    with patch("builtins.open", side_effect=IOError("Read error")):
        # We need to ensure the file "exists" check passes for open to be called
        with patch("os.path.exists", return_value=True):
            engine._load_suppressions()

    mock_app.data_logger.log_error.assert_called_with("Failed to load suppressions: Read error")

def test_save_suppressions_error(setup_coverage_env):
    """Test error handling when saving suppressions fails."""
    mock_logic = MagicMock()
    mock_app = MagicMock()
    engine = InterventionEngine(mock_logic, mock_app)

    engine.suppressed_interventions = {"test": time.time() + 3600}

    with patch("builtins.open", side_effect=IOError("Write error")):
        engine._save_suppressions()

    mock_app.data_logger.log_error.assert_called_with("Failed to save suppressions: Write error")

def test_load_preferences_error(setup_coverage_env):
    """Test error handling when loading preferences fails."""
    mock_logic = MagicMock()
    mock_app = MagicMock()
    engine = InterventionEngine(mock_logic, mock_app)

    with patch("builtins.open", side_effect=IOError("Read error")):
        with patch("os.path.exists", return_value=True):
            engine._load_preferences()

    mock_app.data_logger.log_error.assert_called_with("Failed to load preferences: Read error")

def test_save_preferences_error(setup_coverage_env):
    """Test error handling when saving preferences fails."""
    mock_logic = MagicMock()
    mock_app = MagicMock()
    engine = InterventionEngine(mock_logic, mock_app)

    engine.preferred_interventions = {"test": {"count": 1}}

    with patch("builtins.open", side_effect=IOError("Write error")):
        engine._save_preferences()

    mock_app.data_logger.log_error.assert_called_with("Failed to save preferences: Write error")

def test_speak_linux_fallback(setup_coverage_env):
    """Test TTS fallback logic on Linux."""
    mock_logic = MagicMock()
    mock_app = MagicMock()
    # Explicitly set data_logger to allow logging calls
    mock_app.data_logger = MagicMock()
    engine = InterventionEngine(mock_logic, mock_app)

    # MUST set intervention active for blocking speak to proceed
    engine._intervention_active.set()

    with patch("platform.system", return_value="Linux"):
        # Mock Popen to fail for espeak, then succeed for spd-say
        with patch("subprocess.Popen") as mock_popen:
            # First call raises FileNotFoundError (espeak not found)
            # Second call returns a mock process
            mock_popen.side_effect = [FileNotFoundError, MagicMock()]

            engine._speak("Test message", blocking=True)

            # Check that fallback was attempted
            assert mock_popen.call_count == 2
            # Verify the arguments of the second call
            args, _ = mock_popen.call_args_list[1]
            assert args[0] == ["spd-say", "Test message"]

def test_speak_exception(setup_coverage_env):
    """Test TTS generic exception handling."""
    mock_logic = MagicMock()
    mock_app = MagicMock()
    # Ensure data_logger is a MagicMock so we can check calls
    mock_app.data_logger = MagicMock()
    engine = InterventionEngine(mock_logic, mock_app)

    # MUST set intervention active for blocking speak to proceed
    engine._intervention_active.set()

    with patch("platform.system", return_value="Linux"):
        # Popen is called, raises Exception
        with patch("subprocess.Popen", side_effect=Exception("General failure")):
            engine._speak("Test message", blocking=True)

    # Use any_order=True because _speak logs info before attempting TTS
    # Or just check if log_warning was called at all
    mock_app.data_logger.log_warning.assert_called_with("TTS failed: General failure")

def test_play_sound_missing_libs(setup_coverage_env):
    """Test _play_sound when libraries are missing."""
    mock_logic = MagicMock()
    mock_app = MagicMock()

    # Patch imports in core.intervention_engine to be None
    with patch("core.intervention_engine.sd", None):
        engine = InterventionEngine(mock_logic, mock_app)
        # Create a dummy file so file check passes
        dummy_file = os.path.join(TEST_USER_DATA_DIR, "test.wav")
        with open(dummy_file, 'w') as f: f.write("dummy")

        engine._play_sound(dummy_file)

    mock_app.data_logger.log_warning.assert_called_with("sounddevice or scipy.io.wavfile library not available (or Import failed). Cannot play sound.")

def test_play_sound_file_not_found(setup_coverage_env):
    """Test _play_sound when file does not exist."""
    mock_logic = MagicMock()
    mock_app = MagicMock()
    engine = InterventionEngine(mock_logic, mock_app)

    engine._play_sound("non_existent.wav")
    mock_app.data_logger.log_warning.assert_called()

def test_show_visual_prompt_no_pil(setup_coverage_env):
    """Test _show_visual_prompt when PIL is missing."""
    mock_logic = MagicMock()
    mock_app = MagicMock()

    with patch("core.intervention_engine.Image", None):
        engine = InterventionEngine(mock_logic, mock_app)
        engine._show_visual_prompt("test.jpg")

    mock_app.data_logger.log_warning.assert_called_with("PIL (Pillow) library not available. Cannot show image.")

def test_capture_image_no_cv2(setup_coverage_env):
    """Test _capture_image when cv2 is missing."""
    mock_logic = MagicMock()
    mock_app = MagicMock()
    mock_logic.last_video_frame = "exists"

    with patch("core.intervention_engine.cv2", None):
        engine = InterventionEngine(mock_logic, mock_app)
        engine._capture_image("details")

    mock_app.data_logger.log_warning.assert_called_with("Cannot capture image: OpenCV (cv2) not available.")

def test_capture_image_no_frame(setup_coverage_env):
    """Test _capture_image when no frame is available."""
    mock_logic = MagicMock()
    mock_logic.last_video_frame = None # Explicitly None
    mock_app = MagicMock()

    # Ensure cv2 is "present"
    with patch("core.intervention_engine.cv2", MagicMock()):
        engine = InterventionEngine(mock_logic, mock_app)
        engine._capture_image("details")

    mock_app.data_logger.log_warning.assert_called_with("Cannot capture image: No video frame available in LogicEngine.")

def test_run_sequence_coverage(setup_coverage_env):
    """Test _run_sequence with various actions."""
    mock_logic = MagicMock()
    mock_app = MagicMock()
    engine = InterventionEngine(mock_logic, mock_app)
    engine._intervention_active.set()

    # Mock the action methods to avoid side effects and just verify calls
    engine._speak = MagicMock()
    engine._play_sound = MagicMock()
    engine._show_visual_prompt = MagicMock()
    engine._capture_image = MagicMock()
    engine._record_video = MagicMock()
    engine._wait = MagicMock()

    sequence = [
        {"action": "speak", "content": "Hello"},
        {"action": "sound", "file": "bell.wav"},
        {"action": "visual_prompt", "content": "image.jpg"},
        {"action": "capture_image", "content": "user_face"},
        {"action": "record_video", "content": "clip"},
        {"action": "wait", "duration": 1},
        {"action": "unknown", "content": "what"}
    ]

    engine._run_sequence(sequence, mock_app.data_logger)

    engine._speak.assert_called_with("Hello", blocking=True)
    engine._play_sound.assert_called_with("bell.wav")
    engine._show_visual_prompt.assert_called_with("image.jpg")
    engine._capture_image.assert_called_with("user_face")
    engine._record_video.assert_called_with("clip")
    engine._wait.assert_called_with(1)
    mock_app.data_logger.log_warning.assert_called_with("Unknown action in sequence: unknown")
