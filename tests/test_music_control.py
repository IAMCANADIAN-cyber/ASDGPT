import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add root directory to sys.path
sys.path.append(os.getcwd())

# Mock modules that require display/audio before importing logic_engine
sys.modules['core.music_interface'] = MagicMock()
sys.modules['pyautogui'] = MagicMock()

import config
from core.logic_engine import LogicEngine

class TestMusicControl(unittest.TestCase):

    def setUp(self):
        # Setup mocks
        self.mock_lmm = MagicMock()
        self.mock_music = MagicMock()
        self.mock_logger = MagicMock()

        # Patch config inside logic_engine module
        self.config_patcher = patch('core.logic_engine.config')
        self.mock_config = self.config_patcher.start()

        # Set defaults
        self.mock_config.ENABLE_MUSIC_CONTROL = False
        self.mock_config.LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
        self.mock_config.LMM_CIRCUIT_BREAKER_COOLDOWN = 60
        self.mock_config.HISTORY_WINDOW_SIZE = 5
        self.mock_config.RAPID_SWITCHING_THRESHOLD = 4
        self.mock_config.SEXUAL_AROUSAL_THRESHOLD = 50

        # Initialize LogicEngine
        with patch('core.logic_engine.DataLogger', return_value=self.mock_logger), \
             patch('core.logic_engine.StateEngine'):
            self.logic_engine = LogicEngine(lmm_interface=self.mock_lmm)
            self.logic_engine.music_interface = self.mock_music

    def tearDown(self):
        self.config_patcher.stop()

    def test_music_disabled_by_default(self):
        # Arrange
        self.mock_config.ENABLE_MUSIC_CONTROL = False
        analysis = {"state_estimation": {"arousal": 50, "mood": 50}, "_meta": {"is_fallback": False}}
        self.mock_lmm.process_data.return_value = analysis

        # Act
        payload = {"video_data": None, "audio_data": None, "user_context": {}}
        self.logic_engine._run_lmm_analysis_async(payload, allow_intervention=True)

        # Assert
        self.mock_music.play_mood_playlist.assert_not_called()

    def test_music_enabled_standard_response(self):
        # Arrange
        self.mock_config.ENABLE_MUSIC_CONTROL = True
        analysis = {"state_estimation": {"arousal": 60, "mood": 60}, "_meta": {"is_fallback": False}}
        self.mock_lmm.process_data.return_value = analysis

        # Mock StateEngine state
        self.logic_engine.state_engine.get_state.return_value = {"mood": 60, "arousal": 60, "sexual_arousal": 0}

        # Act
        payload = {"video_data": None, "audio_data": None, "user_context": {}}
        self.logic_engine._run_lmm_analysis_async(payload, allow_intervention=True)

        # Assert
        self.mock_music.play_mood_playlist.assert_called_with(mood=60, arousal=60, sexual_arousal=0)

    def test_music_enabled_fallback_response(self):
        # Arrange
        self.mock_config.ENABLE_MUSIC_CONTROL = True
        # Fallback response should NOT trigger music
        analysis = {"state_estimation": {"arousal": 50, "mood": 50}, "_meta": {"is_fallback": True}}
        self.mock_lmm.process_data.return_value = analysis

        # Act
        payload = {"video_data": None, "audio_data": None, "user_context": {}}
        self.logic_engine._run_lmm_analysis_async(payload, allow_intervention=True)

        # Assert
        self.mock_music.play_mood_playlist.assert_not_called()

if __name__ == '__main__':
    unittest.main()
