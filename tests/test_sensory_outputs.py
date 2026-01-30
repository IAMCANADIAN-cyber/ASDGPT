import unittest
from unittest.mock import MagicMock, patch, ANY
import os
import sys
import platform
import subprocess
import threading
import importlib

# Import is needed to refer to it, but we'll dynamically access it too
import core.intervention_engine

class TestSensoryOutputs(unittest.TestCase):
    def setUp(self):
        # Patch sys.modules to ensure sounddevice is mocked during reload
        self.sd_patcher = patch.dict(sys.modules, {'sounddevice': MagicMock()})
        self.mock_sd = self.sd_patcher.start()

        # Ensure the module is loaded and fresh
        if 'core.intervention_engine' in sys.modules:
            # It exists, so we reload it to pick up the mocked sounddevice
            importlib.reload(sys.modules['core.intervention_engine'])
        else:
            # It doesn't exist (maybe deleted by another test), so we import it
            # Since sounddevice is already mocked in sys.modules, this import will use it.
            import core.intervention_engine

        # Get the class from the module in sys.modules (which is the fresh one)
        self.InterventionEngine = sys.modules['core.intervention_engine'].InterventionEngine

        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MagicMock()
        self.engine = self.InterventionEngine(self.mock_logic, self.mock_app)
        # Ensure intervention is considered active so _speak doesn't abort early
        self.engine._intervention_active.set()

    def tearDown(self):
        self.sd_patcher.stop()
        # Clean up: reload again to restore original state is nice but might be fragile.
        # If we leave it, subsequent tests might use the mocked version.
        # But if they follow the same pattern or don't rely on sounddevice, it's fine.
        # To be safe, we could try to reload if the patcher restored real sounddevice?
        # But sounddevice is likely not installed in this env, so it would fail or return None.
        pass

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_speak_macos(self, mock_popen, mock_system):
        mock_system.return_value = "Darwin"
        self.engine._speak("Hello World", blocking=True)
        mock_popen.assert_called_with(["say", "Hello World"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_speak_linux(self, mock_popen, mock_system):
        mock_system.return_value = "Linux"
        self.engine._speak("Hello World", blocking=True)
        # Should try espeak first
        mock_popen.assert_called_with(["espeak", "Hello World"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @patch('platform.system')
    @patch('subprocess.Popen')
    def test_speak_windows(self, mock_popen, mock_system):
        mock_system.return_value = "Windows"
        self.engine._speak("Hello World", blocking=True)
        expected_command = 'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("Hello World")'
        mock_popen.assert_called_with(["powershell", "-Command", expected_command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @patch('platform.system')
    def test_speak_non_blocking(self, mock_system):
        mock_system.return_value = "Linux"
        # Mock thread start to verify it is called
        with patch('threading.Thread') as mock_thread:
            self.engine._speak("Hello World", blocking=False)
            mock_thread.assert_called_once()

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
