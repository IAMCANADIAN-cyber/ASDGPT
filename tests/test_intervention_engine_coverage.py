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

if __name__ == '__main__':
    unittest.main()
