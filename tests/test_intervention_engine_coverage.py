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
