import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
import importlib

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestMainFeedbackIntegration(unittest.TestCase):
    def setUp(self):
        # 1. Patch sys.modules for ALL heavy/hardware dependencies
        self.modules_patcher = patch.dict(sys.modules, {
            "pystray": MagicMock(),
            "PIL": MagicMock(),
            "PIL.Image": MagicMock(),
            "PIL.ImageDraw": MagicMock(),
            "sounddevice": MagicMock(),
            "cv2": MagicMock(),
            "numpy": MagicMock(),
            "keyboard": MagicMock(),
            "dotenv": MagicMock(),
            "requests": MagicMock(),
            "core.system_tray": MagicMock(), # We might want to mock the class specifically
        })
        self.modules_patcher.start()

        # 2. Setup config
        self.config_mock = MagicMock()
        self.config_mock.LOG_FILE = "test_app.log"
        self.config_mock.CAMERA_INDEX = 0
        self.config_mock.HOTKEY_CYCLE_MODE = "ctrl+alt+m"
        self.config_mock.HOTKEY_PAUSE_RESUME = "ctrl+alt+p"
        self.config_mock.HOTKEY_FEEDBACK_HELPFUL = "ctrl+alt+h"
        self.config_mock.HOTKEY_FEEDBACK_UNHELPFUL = "ctrl+alt+u"
        self.config_mock.APP_NAME = "ASDGPT"
        sys.modules["config"] = self.config_mock

        # 3. Import main
        import main
        importlib.reload(main)
        self.Application = main.Application

    def tearDown(self):
        self.modules_patcher.stop()

    @patch('main.AudioSensor')
    @patch('main.VideoSensor')
    @patch('main.LMMInterface')
    @patch('main.LogicEngine')
    @patch('main.InterventionEngine')
    @patch('main.DataLogger')
    @patch('main.ACRTrayIcon')
    def test_feedback_hotkeys_trigger_visuals(self, MockTray, MockLogger, MockIE, MockLE, MockLMM, MockVideo, MockAudio):
        """Test that feedback hotkeys trigger the correct visual flash."""

        # Setup mocks
        app = self.Application()

        # Verify initial setup
        app.tray_icon = MockTray.return_value
        app.logic_engine = MockLE.return_value
        app.logic_engine.get_mode.return_value = "active"

        # Test Helpful Feedback
        app.on_feedback_helpful_pressed()

        # It should register feedback
        app.intervention_engine.register_feedback.assert_called_with("helpful")

        # It should flash the tray icon with 'feedback_helpful' (green)
        # Current implementation flashes logic_engine.get_mode() ("active"), so this assertion is expected to fail initially
        app.tray_icon.flash_icon.assert_called_with(flash_status="feedback_helpful", duration=0.3, flashes=1)

        # Test Unhelpful Feedback
        app.on_feedback_unhelpful_pressed()

        app.intervention_engine.register_feedback.assert_called_with("unhelpful")
        app.tray_icon.flash_icon.assert_called_with(flash_status="feedback_unhelpful", duration=0.3, flashes=1)

if __name__ == "__main__":
    unittest.main()
