import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
# Import main directly. It should be safe as it doesn't import keyboard at top level.
from main import Application

class TestEcoMode(unittest.TestCase):
    def setUp(self):
        # We need to mock things before instantiating Application to avoid heavy startup
        self.mock_logger = MagicMock()
        self.mock_video = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_logic = MagicMock()

        # Patch dependencies that Application.__init__ creates
        self.patcher_logger = patch('main.DataLogger', return_value=self.mock_logger)
        self.patcher_video = patch('main.VideoSensor', return_value=self.mock_video)
        self.patcher_audio = patch('main.AudioSensor', return_value=self.mock_audio)
        self.patcher_logic = patch('main.LogicEngine', return_value=self.mock_logic)
        self.patcher_lmm = patch('main.LMMInterface', MagicMock())
        self.patcher_tray = patch('main.ACRTrayIcon', MagicMock())
        self.patcher_ie = patch('main.InterventionEngine', MagicMock())

        # Patch sys.modules to mock keyboard which is imported in _setup_hotkeys
        self.patcher_keyboard_module = patch.dict(sys.modules, {'keyboard': MagicMock()})

        # Start patches
        self.patcher_logger.start()
        self.patcher_video.start()
        self.patcher_audio.start()
        self.patcher_logic.start()
        self.patcher_lmm.start()
        self.patcher_tray.start()
        self.patcher_ie.start()
        self.patcher_keyboard_module.start()

        # Instantiate Application
        self.app = Application()
        # Ensure logic engine is our mock (though patch should have handled it)
        self.app.logic_engine = self.mock_logic

    def tearDown(self):
        patch.stopall()

    def test_eco_mode_active_when_face_detected(self):
        """Verify delay corresponds to Active Mode when face is detected."""
        self.mock_logic.face_metrics = {"face_detected": True}

        delay = self.app._get_video_poll_delay()

        self.assertEqual(delay, config.VIDEO_ACTIVE_DELAY)

    def test_eco_mode_active_when_face_not_detected(self):
        """Verify delay corresponds to Eco Mode when face is NOT detected."""
        self.mock_logic.face_metrics = {"face_detected": False}

        delay = self.app._get_video_poll_delay()

        self.assertEqual(delay, config.VIDEO_ECO_MODE_DELAY)

    def test_eco_mode_defaults_to_eco_if_missing_metrics(self):
        """Verify defaults to Eco Mode if metrics are empty/missing key."""
        self.mock_logic.face_metrics = {}

        delay = self.app._get_video_poll_delay()

        self.assertEqual(delay, config.VIDEO_ECO_MODE_DELAY)

if __name__ == '__main__':
    unittest.main()
