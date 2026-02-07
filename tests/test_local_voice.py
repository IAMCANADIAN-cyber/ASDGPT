import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import config
import sys

# Mock whisper and TTS to avoid loading models
sys.modules['whisper'] = MagicMock()
sys.modules['TTS'] = MagicMock()
sys.modules['TTS.api'] = MagicMock()

# Reload STTInterface and VoiceInterface to pick up mocks
import core.stt_interface
from importlib import reload
reload(core.stt_interface)
from core.stt_interface import STTInterface

import core.voice_interface
reload(core.voice_interface)
from core.voice_interface import VoiceInterface

class TestLocalVoiceFeatures(unittest.TestCase):

    def test_stt_whisper_path(self):
        # Mock availability of whisper
        core.stt_interface.whisper = MagicMock()

        stt = STTInterface(logger=MagicMock(), model_size="tiny")
        self.assertEqual(stt.engine, "whisper")

        # Mock transcription
        mock_model = stt.whisper_model
        mock_model.transcribe.return_value = {"text": "Hello world"}

        # Test 44.1k input (requires resampling logic check)
        audio = np.random.uniform(-1, 1, 44100).astype(np.float32)
        text = stt.transcribe(audio, 44100)

        self.assertEqual(text, "Hello world")
        mock_model.transcribe.assert_called()

        # Verify resampling happened (input to transcribe should be length 16000)
        args, _ = mock_model.transcribe.call_args
        self.assertEqual(len(args[0]), 16000)

    def test_voice_interface_coqui(self):
        # Mock Config
        with patch.object(config, 'TTS_ENGINE', 'coqui'):
            # Mock TTS class
            mock_tts_class = core.voice_interface.TTS
            # Logic: TTS().to("cpu") returns the engine
            mock_engine = mock_tts_class.return_value.to.return_value

            vi = VoiceInterface(logger=MagicMock())
            self.assertEqual(vi.engine_type, "coqui")

            # Test speak
            with patch('os.system') as mock_os:
                vi._speak_coqui("Test")
                mock_engine.tts_to_file.assert_called()

    def test_voice_interface_system_fallback(self):
        # If Coqui fails to load, should fallback
        core.voice_interface.TTS = None # Simulate missing
        with patch.object(config, 'TTS_ENGINE', 'coqui'):
            vi = VoiceInterface(logger=MagicMock())
            self.assertEqual(vi.engine_type, "system")

if __name__ == '__main__':
    unittest.main()
