import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib

# Ensure root directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestUXFeedbackIntegration(unittest.TestCase):
    def setUp(self):
        # Patch sys.modules to mock external dependencies BEFORE importing main
        self.modules_patcher = patch.dict(sys.modules, {
            "requests": MagicMock(),
            "numpy": MagicMock(),
            "cv2": MagicMock(),
            "sounddevice": MagicMock(),
            "pystray": MagicMock(),
            "PIL": MagicMock(),
            "PIL.Image": MagicMock(),
            "PIL.ImageDraw": MagicMock(),
            "keyboard": MagicMock(),
            "config": MagicMock(),
        })
        self.modules_patcher.start()

        # Setup config
        sys.modules["config"].APP_NAME = "ASDGPT"
        sys.modules["config"].LOG_FILE = "test.log"
        sys.modules["config"].LOG_LEVEL = "INFO"
        sys.modules["config"].CAMERA_INDEX = 0
        sys.modules["config"].HOTKEY_CYCLE_MODE = "m"
        sys.modules["config"].HOTKEY_PAUSE_RESUME = "p"
        sys.modules["config"].HOTKEY_FEEDBACK_HELPFUL = "h"
        sys.modules["config"].HOTKEY_FEEDBACK_UNHELPFUL = "u"
        sys.modules["config"].SNOOZE_DURATION = 3600
        sys.modules["config"].DEFAULT_MODE = "active"
        sys.modules["config"].AUDIO_THRESHOLD_HIGH = 0.5
        sys.modules["config"].VIDEO_ACTIVITY_THRESHOLD_HIGH = 20.0
        sys.modules["config"].LMM_CIRCUIT_BREAKER_MAX_FAILURES = 5
        sys.modules["config"].LMM_CIRCUIT_BREAKER_COOLDOWN = 60

        # We need to reload main to ensure it picks up the mocked modules
        import main
        importlib.reload(main)
        self.main_module = main

    def tearDown(self):
        self.modules_patcher.stop()

    def test_feedback_triggers_correct_icons(self):
        # Initialize App with mocked components
        app = self.main_module.Application()

        # Mock the tray icon specifically to capture calls
        app.tray_icon = MagicMock()

        # Mock logic engine mode to be "active"
        app.logic_engine.get_mode = MagicMock(return_value="active")

        # 1. Test Helpful Feedback
        app.on_feedback_helpful_pressed()

        # Assert flash_icon was called
        # CURRENTLY (BUG): called with flash_status="active" (result of get_mode())
        # DESIRED: flash_status="feedback_helpful"

        # We expect this assertion to FAIL until we fix main.py
        app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_helpful",
            duration=0.3,
            flashes=1
        )

        # Reset mock
        app.tray_icon.flash_icon.reset_mock()

        # 2. Test Unhelpful Feedback
        app.on_feedback_unhelpful_pressed()

        # We expect this assertion to FAIL until we fix main.py
        app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_unhelpful",
            duration=0.3,
            flashes=1
        )

if __name__ == "__main__":
    unittest.main()
