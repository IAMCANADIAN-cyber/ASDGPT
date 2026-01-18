import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import builtins
import subprocess

from core.intervention_engine import InterventionEngine
import core.intervention_engine as ie_module

class TestInterventionEngineCoverage(unittest.TestCase):
    def setUp(self):
        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MagicMock()
        self.mock_app.data_logger = MagicMock()

        # Instantiate with mocks
        self.engine = InterventionEngine(self.mock_logic, self.mock_app)
        # Activating intervention by default for TTS tests that check blocking
        self.engine._intervention_active.set()

    def test_load_suppressions_file_error(self):
        """Test graceful handling of file read errors for suppressions."""
        with patch('builtins.open', side_effect=OSError("Read permission denied")):
            with patch('os.path.exists', return_value=True):
                self.engine._load_suppressions()
                # Should log error, not crash
                self.mock_app.data_logger.log_error.assert_called()
                args, _ = self.mock_app.data_logger.log_error.call_args
                assert "Failed to load suppressions" in args[0]

    def test_save_suppressions_file_error(self):
        """Test graceful handling of file write errors for suppressions."""
        # Use a non-empty dict so it tries to save
        self.engine.suppressed_interventions = {"test": 1234567890}

        with patch('builtins.open', side_effect=OSError("Write permission denied")):
            self.engine._save_suppressions()
            # Should log error
            self.mock_app.data_logger.log_error.assert_called()
            args, _ = self.mock_app.data_logger.log_error.call_args
            assert "Failed to save suppressions" in args[0]

    def test_load_preferences_json_error(self):
        """Test graceful handling of corrupted JSON in preferences."""
        # Simulate invalid JSON
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "{invalid_json}"

        with patch('builtins.open', return_value=mock_file): # Just returning a mock, but json.load will fail if we don't mock it or the file content
            with patch('json.load', side_effect=ValueError("Expecting value")):
                with patch('os.path.exists', return_value=True):
                    self.engine._load_preferences()
                    self.mock_app.data_logger.log_error.assert_called()
                    args, _ = self.mock_app.data_logger.log_error.call_args
                    assert "Failed to load preferences" in args[0]

    def test_missing_cv2_capture(self):
        """Test capture_image when cv2 is missing."""
        with patch.object(ie_module, 'cv2', None):
            self.engine.logic_engine.last_video_frame = "some_frame"
            self.engine._capture_image("test_details")

            self.mock_app.data_logger.log_warning.assert_called()
            args, _ = self.mock_app.data_logger.log_warning.call_args
            assert "OpenCV (cv2) not available" in args[0]

    def test_missing_pil_visual_prompt(self):
        """Test show_visual_prompt when PIL is missing."""
        with patch.object(ie_module, 'Image', None):
            self.engine._show_visual_prompt("some_image.jpg")

            self.mock_app.data_logger.log_warning.assert_called()
            args, _ = self.mock_app.data_logger.log_warning.call_args
            assert "PIL (Pillow) library not available" in args[0]

    def test_missing_sounddevice_play_sound(self):
        """Test play_sound when sounddevice is missing."""
        with patch.object(ie_module, 'sd', None):
            with patch('os.path.exists', return_value=True):
                self.engine._play_sound("test.wav")

                self.mock_app.data_logger.log_warning.assert_called()
                args, _ = self.mock_app.data_logger.log_warning.call_args
                assert "sounddevice" in args[0]

    @patch('platform.system', return_value='Linux')
    def test_tts_fallback_linux(self, mock_system):
        """Test fallback from espeak to spd-say on Linux."""

        # We need to test _speak, but it launches a thread or runs directly.
        # It calls Popen. We want to simulate Popen failing for espeak (FileNotFoundError)
        # and succeeding for spd-say.

        # The _speak method constructs command=["espeak", text]

        def side_effect(command, **kwargs):
            if command[0] == "espeak":
                raise FileNotFoundError("espeak not found")
            return MagicMock() # Return a mock process for spd-say

        with patch('subprocess.Popen', side_effect=side_effect) as mock_popen:
            self.engine._speak("Hello", blocking=True)

            # Verify attempts
            # Should have tried espeak first
            calls = mock_popen.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0][0] == "espeak"
            assert calls[1][0][0][0] == "spd-say"

    @patch('platform.system', return_value='Darwin')
    def test_tts_failure_macos(self, mock_system):
        """Test generic TTS failure handling (e.g. on macOS)."""

        with patch('subprocess.Popen', side_effect=Exception("General failure")):
            self.engine._speak("Hello", blocking=True)

            self.mock_app.data_logger.log_warning.assert_called()
            args, _ = self.mock_app.data_logger.log_warning.call_args
            assert "TTS failed" in args[0]

    def test_record_video_no_frame(self):
        """Test _record_video logic when no frame is available."""
        self.engine.logic_engine.last_video_frame = None
        self.engine._record_video("test")
        self.mock_app.data_logger.log_warning.assert_called()
        args, _ = self.mock_app.data_logger.log_warning.call_args
        assert "Signal lost" in args[0]

    def test_record_video_no_attribute(self):
        """Test _record_video logic when LogicEngine lacks last_video_frame attribute."""
        del self.engine.logic_engine.last_video_frame
        self.engine._record_video("test")
        self.mock_app.data_logger.log_warning.assert_called()
        args, _ = self.mock_app.data_logger.log_warning.call_args
        assert "No video frame available" in args[0]
        # Restore attribute for other tests
        self.engine.logic_engine.last_video_frame = MagicMock()

    def test_record_video_no_cv2(self):
        """Test _record_video logic when cv2 is missing."""
        with patch.object(ie_module, 'cv2', None):
            self.engine.logic_engine.last_video_frame = MagicMock()
            self.engine._record_video("test")
            self.mock_app.data_logger.log_warning.assert_called()
            args, _ = self.mock_app.data_logger.log_warning.call_args
            assert "OpenCV (cv2) not available" in args[0]

    @patch('core.intervention_engine.time')
    @patch('core.intervention_engine.cv2')
    @patch('core.intervention_engine.os.makedirs')
    @patch('core.intervention_engine.os.path.exists')
    def test_record_video_success_fast(self, mock_exists, mock_makedirs, mock_cv2, mock_time):
        """Test _record_video success path with time mocked to exit loop immediately."""
        mock_frame = MagicMock()
        mock_frame.shape = (480, 640, 3)
        self.engine.logic_engine.last_video_frame = mock_frame
        mock_exists.return_value = False

        mock_writer = mock_cv2.VideoWriter.return_value
        mock_time.sleep.return_value = None

        # Scenario 1: Immediate exit (loop logic check)
        # Mock time sequence: start=0, check>5 -> exit
        mock_time.time.side_effect = [0, 6.0]
        self.engine._record_video("test_immediate")

        mock_cv2.VideoWriter.assert_called()
        mock_writer.release.assert_called()

        # Reset mocks for Scenario 2
        mock_cv2.VideoWriter.reset_mock()
        mock_writer.reset_mock()

        # Scenario 2: One frame captured
        # Mock time sequence: start=0, check1=1.0 (<5, continue), check2=6.0 (>5, exit)
        mock_time.time.side_effect = [0, 1.0, 6.0]

        self.engine._record_video("test_one_frame")

        mock_writer.write.assert_called()
        mock_writer.release.assert_called_once()

    @patch('core.intervention_engine.wavfile')
    @patch('core.intervention_engine.sd')
    @patch('core.intervention_engine.os.path.exists')
    def test_play_sound_success(self, mock_exists, mock_sd, mock_wavfile):
        """Test _play_sound success path."""
        mock_exists.return_value = True
        mock_wavfile.read.return_value = (44100, "data")

        self.engine._play_sound("test.wav")

        mock_sd.play.assert_called_with("data", 44100)
        mock_sd.wait.assert_called_once()

    def test_show_visual_prompt_success_image(self):
        """Test _show_visual_prompt with valid image path."""
        with patch('core.intervention_engine.Image') as mock_image:
            with patch('core.intervention_engine.os.path.exists', return_value=True):
                self.engine._show_visual_prompt("test.jpg")
                mock_image.open.assert_called_with("test.jpg")
                mock_image.open.return_value.show.assert_called_once()

    def test_show_visual_prompt_text_only(self):
        """Test _show_visual_prompt with text (path does not exist)."""
        with patch('core.intervention_engine.os.path.exists', return_value=False):
             self.engine._show_visual_prompt("Just some text")
             # Should just log, no crash
             self.mock_app.data_logger.log_info.assert_called()

    def test_shutdown(self):
        """Test shutdown cleans up resources."""
        self.engine.intervention_thread = MagicMock()
        self.engine.intervention_thread.is_alive.return_value = True

        with patch.object(ie_module, 'sd') as mock_sd:
            self.engine.shutdown()

            # Verify stop called
            self.assertFalse(self.engine._intervention_active.is_set())
            mock_sd.stop.assert_called_once()
            self.engine.intervention_thread.join.assert_called()

    def test_get_preferred_intervention_types(self):
        """Test getting preferred interventions sorted."""
        self.engine.preferred_interventions = {
            "low_pref": {"count": 1},
            "high_pref": {"count": 10},
            "mid_pref": {"count": 5}
        }

        prefs = self.engine.get_preferred_intervention_types()
        self.assertEqual(prefs, ["high_pref", "mid_pref", "low_pref"])

    def test_notify_mode_change(self):
        """Test notify_mode_change triggers speech."""
        with patch.object(self.engine, '_speak') as mock_speak:
            self.engine.notify_mode_change("paused")
            mock_speak.assert_called_with("Co-regulator paused.", blocking=False)

            self.engine.notify_mode_change("active", custom_message="Custom")
            mock_speak.assert_called_with("Custom", blocking=False)

if __name__ == '__main__':
    unittest.main()
import pytest
from unittest.mock import MagicMock, patch, ANY, call
import time
import os
import json
import threading
import sys

# Mock config before imports
sys.modules['config'] = MagicMock()
sys.modules['config'].FEEDBACK_WINDOW_SECONDS = 5
sys.modules['config'].MIN_TIME_BETWEEN_INTERVENTIONS = 0.1
sys.modules['config'].FEEDBACK_SUPPRESSION_MINUTES = 60
sys.modules['config'].SUPPRESSIONS_FILE = "suppressions.json"
sys.modules['config'].PREFERENCES_FILE = "preferences.json"
sys.modules['config'].SNOOZE_DURATION = 60

from core.intervention_engine import InterventionEngine

class TestInterventionEngineCoverage:
    @pytest.fixture
    def mock_logic_engine(self):
        le = MagicMock()
        le.get_mode.return_value = "active"
        le.last_video_frame = None # Default
        return le

    @pytest.fixture
    def mock_app(self):
        app = MagicMock()
        app.data_logger = MagicMock()
        app.tray_icon = MagicMock()
        return app

    @pytest.fixture
    def engine(self, mock_logic_engine, mock_app):
        # Patch load/save to avoid file IO during init
        with patch.object(InterventionEngine, '_load_suppressions'), \
             patch.object(InterventionEngine, '_load_preferences'):
            ie = InterventionEngine(mock_logic_engine, mock_app)
            return ie

    def test_init(self, engine):
        assert engine.library is not None
        assert engine._intervention_active is not None

    def test_load_save_suppressions(self, engine):
        # We need to test the actual file IO logic, but safely
        # Using mocks for open/json
        with patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('json.load') as mock_json_load, \
             patch('os.path.exists', return_value=True):

            mock_json_load.return_value = {"test_type": time.time() + 100}
            engine._load_suppressions()
            assert "test_type" in engine.suppressed_interventions

        # Verify save works
        with patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('json.dump') as mock_json_dump, \
             patch('os.makedirs'):

            engine._save_suppressions()
            mock_json_dump.assert_called_once()


    def test_load_save_preferences(self, engine):
        with patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('json.load') as mock_json_load, \
             patch('os.path.exists', return_value=True):

            mock_json_load.return_value = {"test_type": {"count": 1}}
            engine._load_preferences()
            assert "test_type" in engine.preferred_interventions

        with patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('json.dump') as mock_json_dump, \
             patch('os.makedirs'):

            engine._save_preferences()
            mock_json_dump.assert_called_once()

    def test_speak_platform(self, engine):
        # Ensure intervention is active so blocking speak proceeds
        engine._intervention_active.set()

        with patch('platform.system', return_value="Linux"), \
             patch('subprocess.Popen') as mock_popen:

            engine._speak("Test", blocking=True)
            mock_popen.assert_called()

    def test_play_sound_missing_file(self, engine):
        with patch('os.path.exists', return_value=False):
            engine._play_sound("missing.wav")
            engine.app.data_logger.log_warning.assert_called()

    def test_show_visual_prompt(self, engine):
        # Mock Image
        with patch('core.intervention_engine.Image') as MockImage:
            with patch('os.path.exists', return_value=True):
                engine._show_visual_prompt("test.jpg")
                MockImage.open.assert_called_with("test.jpg")

    def test_capture_image(self, engine):
        # Mock cv2
        with patch('core.intervention_engine.cv2') as mock_cv2:
            engine.logic_engine.last_video_frame = "frame_data"
            with patch('os.path.exists', return_value=False), \
                 patch('os.makedirs'):
                engine._capture_image("details")
                mock_cv2.imwrite.assert_called()

    def test_record_video(self, engine):
         with patch('core.intervention_engine.cv2') as mock_cv2:
            mock_frame = MagicMock()
            mock_frame.shape = (100, 100, 3)
            engine.logic_engine.last_video_frame = mock_frame

            with patch('os.path.exists', return_value=False), \
                 patch('os.makedirs'), \
                 patch('time.sleep'): # Speed up loop
                # Ensure intervention is active
                engine._intervention_active.set()
                engine._record_video("details")
                mock_cv2.VideoWriter.assert_called()

    def test_wait(self, engine):
        start = time.time()
        engine._intervention_active.set()
        # Mock sleep to return immediately or run fast
        with patch('time.sleep'):
             # We can't easily mock time.time() to increment in a loop without side effects
             # So we just test that it respects the flag
             engine._intervention_active.clear() # Should exit loop immediately
             engine._wait(10)
        # Should be fast
        assert time.time() - start < 1

    def test_run_sequence(self, engine):
        sequence = [
            {"action": "speak", "content": "hi"},
            {"action": "wait", "duration": 0},
            {"action": "unknown"}
        ]
        engine._intervention_active.set()

        with patch.object(engine, '_speak') as mock_speak, \
             patch.object(engine, '_wait') as mock_wait:

            engine._run_sequence(sequence, engine.app.data_logger)
            mock_speak.assert_called()
            mock_wait.assert_called()
            engine.app.data_logger.log_warning.assert_called_with("Unknown action in sequence: unknown")

    def test_suppress_intervention(self, engine):
        with patch.object(engine, '_save_suppressions'):
            engine.suppress_intervention("test", 10)
            assert "test" in engine.suppressed_interventions
            assert engine.suppressed_interventions["test"] > time.time()

    def test_get_suppressed_intervention_types(self, engine):
        engine.suppressed_interventions = {
            "valid": time.time() + 100,
            "expired": time.time() - 100
        }
        with patch.object(engine, '_save_suppressions'):
            active = engine.get_suppressed_intervention_types()
            assert "valid" in active
            assert "expired" not in active
            assert "expired" not in engine.suppressed_interventions

    def test_get_preferred_intervention_types(self, engine):
        engine.preferred_interventions = {
            "a": {"count": 5},
            "b": {"count": 10}
        }
        prefs = engine.get_preferred_intervention_types()
        assert prefs == ["b", "a"]

    def test_start_intervention_success(self, engine):
        details = {"type": "test", "message": "msg"}

        with patch('threading.Thread'):
             result = engine.start_intervention(details)
             assert result is True
             assert engine._intervention_active.is_set()

    def test_start_intervention_suppressed(self, engine):
        details = {"type": "test", "message": "msg"}
        engine.suppressed_interventions = {"test": time.time() + 100}

        result = engine.start_intervention(details)
        assert result is False

    def test_start_intervention_mode_check(self, engine):
        details = {"type": "test", "message": "msg"}
        engine.logic_engine.get_mode.return_value = "paused"

        result = engine.start_intervention(details)
        assert result is False

    def test_start_intervention_rate_limit(self, engine):
        details = {"type": "test", "message": "msg"}
        engine.last_intervention_time = time.time()

        result = engine.start_intervention(details)
        assert result is False

    def test_start_intervention_priority(self, engine):
        # Set active intervention
        engine._intervention_active.set()
        engine._current_intervention_details = {"tier": 1}

        details_high = {"type": "high", "message": "urgent", "tier": 2}

        with patch('threading.Thread'), patch.object(engine, 'stop_intervention') as mock_stop:
            result = engine.start_intervention(details_high)
            assert result is True
            mock_stop.assert_called()

        # Low priority should fail
        engine._intervention_active.set()
        engine._current_intervention_details = {"tier": 2}
        details_low = {"type": "low", "message": "meh", "tier": 1}

        result = engine.start_intervention(details_low)
        assert result is False

    def test_stop_intervention(self, engine):
        engine._intervention_active.set()
        engine._current_subprocess = MagicMock()

        engine.stop_intervention()

        assert not engine._intervention_active.is_set()
        engine._current_subprocess.terminate.assert_called()

    def test_notify_mode_change(self, engine):
        with patch.object(engine, '_speak') as mock_speak:
            engine.notify_mode_change("paused")
            mock_speak.assert_called_with("Co-regulator paused.", blocking=False)

    def test_register_feedback_valid(self, engine):
        engine.last_feedback_eligible_intervention = {
            "message": "msg",
            "type": "type",
            "timestamp": time.time()
        }

        with patch.object(engine, '_save_preferences'):
            engine.register_feedback("helpful")
            assert "type" in engine.preferred_interventions
            assert engine.preferred_interventions["type"]["count"] == 1

    def test_register_feedback_unhelpful(self, engine):
        engine.last_feedback_eligible_intervention = {
            "message": "msg",
            "type": "type",
            "timestamp": time.time()
        }

        with patch.object(engine, 'suppress_intervention') as mock_suppress:
            engine.register_feedback("unhelpful")
            mock_suppress.assert_called()

    def test_register_feedback_expired(self, engine):
        engine.last_feedback_eligible_intervention = {
            "message": "msg",
            "type": "type",
            "timestamp": time.time() - 100
        }

        engine.register_feedback("helpful")
        # Should do nothing (check log calls if needed, or lack of preference update)
        assert "type" not in engine.preferred_interventions

    def test_shutdown(self, engine):
        engine.shutdown()
        assert not engine._intervention_active.is_set()
