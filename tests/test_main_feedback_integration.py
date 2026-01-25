import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 1. PRE-IMPORT MOCKING
# We must mock these BEFORE importing main, because main imports them at top level (transitively)
mock_modules = [
    "sounddevice",
    "cv2",
    "pystray",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "numpy",
    "keyboard",
    "requests",
    "dotenv"
]
for mod in mock_modules:
    sys.modules[mod] = MagicMock()

# Now we can safely import main
import main
import config

class TestMainFeedbackIntegration(unittest.TestCase):
    def setUp(self):
        # 2. CONFIG PATCHING
        # Ensure config has necessary attributes
        self.config_patcher = patch.multiple('config',
            LOG_FILE="test.log",
            CAMERA_INDEX=0,
            HOTKEY_CYCLE_MODE="ctrl+alt+m",
            HOTKEY_PAUSE_RESUME="ctrl+alt+p",
            HOTKEY_FEEDBACK_HELPFUL="ctrl+alt+up",
            HOTKEY_FEEDBACK_UNHELPFUL="ctrl+alt+down",
            LOG_LEVEL="INFO",
            FEEDBACK_WINDOW_SECONDS=15
        )
        self.config_patcher.start()

        # 3. CLASS PATCHING
        # We need to mock the classes instantiated in Application.__init__
        # main.py imports them like: from sensors.video_sensor import VideoSensor
        # so we patch 'main.VideoSensor', etc.

        self.patchers = {
            'video': patch('main.VideoSensor'),
            'audio': patch('main.AudioSensor'),
            'lmm': patch('main.LMMInterface'),
            'logic': patch('main.LogicEngine'),
            'intervention': patch('main.InterventionEngine'),
            'tray': patch('main.ACRTrayIcon'),
            'logger': patch('main.DataLogger')
        }

        self.mocks = {}
        for name, patcher in self.patchers.items():
            self.mocks[name] = patcher.start()

    def tearDown(self):
        self.config_patcher.stop()
        for patcher in self.patchers.values():
            patcher.stop()

    def test_feedback_helpful_visuals(self):
        """Verify that helpful feedback triggers the specific 'feedback_helpful' icon flash."""
        app = main.Application()

        # Setup mocks
        app.logic_engine.get_mode.return_value = "active"

        # Action
        app.on_feedback_helpful_pressed()

        # Assertion
        # It currently (buggy) calls with get_mode() result ("active")
        # We want it to call with "feedback_helpful"
        app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_helpful",
            duration=0.3,
            flashes=1
        )

    def test_feedback_unhelpful_visuals(self):
        """Verify that unhelpful feedback triggers the specific 'feedback_unhelpful' icon flash."""
        app = main.Application()

        # Setup mocks
        app.logic_engine.get_mode.return_value = "active"

        # Action
        app.on_feedback_unhelpful_pressed()

        # Assertion
        app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_unhelpful",
            duration=0.3,
            flashes=1
        )

if __name__ == '__main__':
    unittest.main()
