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
        # Ensure intervention is considered active so _speak doesn't abort early
        self.engine._intervention_active.set()

    def test_speak_delegates_to_voice_interface(self):
        # We only need to test delegation, as platform specifics are in VoiceInterface tests
        self.engine.voice_interface = MagicMock()

        self.engine._speak("Hello World", blocking=True)
        self.engine.voice_interface.speak.assert_called_with("Hello World", True)

        self.engine._speak("Hello Again", blocking=False)
        self.engine.voice_interface.speak.assert_called_with("Hello Again", False)

    @patch('core.intervention_engine.sd')
    @patch('core.intervention_engine.wavfile')
    @patch('os.path.exists')
    def test_play_sound(self, mock_exists, mock_wavfile, mock_sd):
        mock_exists.return_value = True
        mock_wavfile.read.return_value = (44100, [0, 1, 0])

        self.engine._play_sound("dummy.wav")

        mock_sd.play.assert_called()
        # sd.wait is called to block
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
