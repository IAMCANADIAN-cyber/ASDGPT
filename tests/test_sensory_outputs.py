import unittest
from unittest.mock import MagicMock, patch, ANY
import os
import sys
import platform
import subprocess
import threading

# Mock sounddevice before importing InterventionEngine
sys.modules['sounddevice'] = MagicMock()

from core.intervention_engine import InterventionEngine

class TestSensoryOutputs(unittest.TestCase):
    def setUp(self):
        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MagicMock()
        self.engine = InterventionEngine(self.mock_logic, self.mock_app)

    @patch('platform.system')
    @patch('subprocess.run')
    def test_speak_macos(self, mock_run, mock_system):
        mock_system.return_value = "Darwin"
        self.engine._speak("Hello World", blocking=True)
        mock_run.assert_called_with(["say", "Hello World"], check=False)

    @patch('platform.system')
    @patch('subprocess.run')
    def test_speak_linux(self, mock_run, mock_system):
        mock_system.return_value = "Linux"
        self.engine._speak("Hello World", blocking=True)
        # Should try espeak first
        mock_run.assert_called_with(["espeak", "Hello World"], check=False)

    @patch('platform.system')
    @patch('subprocess.run')
    def test_speak_windows(self, mock_run, mock_system):
        mock_system.return_value = "Windows"
        self.engine._speak("Hello World", blocking=True)
        expected_command = 'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("Hello World")'
        mock_run.assert_called_with(["powershell", "-Command", expected_command], check=False)

    @patch('platform.system')
    @patch('subprocess.run')
    def test_speak_non_blocking(self, mock_run, mock_system):
        mock_system.return_value = "Linux"
        # Mock thread start to verify it is called
        with patch('threading.Thread') as mock_thread:
            self.engine._speak("Hello World", blocking=False)
            mock_thread.assert_called_once()
            # We can't easily check subprocess call inside the thread without more complex mocking,
            # but verifying thread start is sufficient for "non-blocking" check.

    @patch('core.intervention_engine.sd')
    @patch('core.intervention_engine.wavfile')
    @patch('os.path.exists')
    def test_play_sound(self, mock_exists, mock_wavfile, mock_sd):
        mock_exists.return_value = True
        mock_wavfile.read.return_value = (44100, [0, 1, 0])

        self.engine._play_sound("dummy.wav")

        mock_sd.play.assert_called()
        mock_sd.wait.assert_called()

    @patch('core.intervention_engine.sd', None)
    @patch('os.path.exists')
    def test_play_sound_no_sounddevice(self, mock_exists):
        # When sd is None (import failed), it should log warning and not crash
        mock_exists.return_value = True
        self.engine._play_sound("dummy.wav")
        self.mock_app.data_logger.log_warning.assert_called_with("sounddevice or scipy.io.wavfile library not available (or Import failed). Cannot play sound.")

    @patch('core.intervention_engine.Image.open')
    @patch('os.path.exists')
    def test_show_visual_prompt(self, mock_exists, mock_open):
        mock_exists.return_value = True
        mock_img = MagicMock()
        mock_open.return_value = mock_img

        self.engine._show_visual_prompt("test.png")

        mock_open.assert_called_with("test.png")
        mock_img.show.assert_called()

if __name__ == '__main__':
    unittest.main()
