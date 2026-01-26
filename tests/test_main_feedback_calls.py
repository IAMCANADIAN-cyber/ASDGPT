import unittest
from unittest.mock import MagicMock, patch
import sys
import importlib

class TestMainFeedbackCalls(unittest.TestCase):
    def setUp(self):
        # Patch sys.modules to mock heavy dependencies
        self.modules_patcher = patch.dict(sys.modules, {
            "sounddevice": MagicMock(),
            "cv2": MagicMock(),
            "pystray": MagicMock(),
            "PIL": MagicMock(),
            "PIL.Image": MagicMock(),
            "PIL.ImageDraw": MagicMock(),
            "keyboard": MagicMock(),
            "sensors": MagicMock(),
            "sensors.video_sensor": MagicMock(),
            "sensors.audio_sensor": MagicMock(),
            "numpy": MagicMock(),
            "requests": MagicMock(),
            "dotenv": MagicMock(),
        })
        self.modules_patcher.start()

        # Now import main
        # We need to ensure we get a fresh import to apply mocks
        if 'main' in sys.modules:
            del sys.modules['main']
        import main
        self.main_module = main

    def tearDown(self):
        self.modules_patcher.stop()

    def test_feedback_helpful_flash(self):
        # Setup
        app = self.main_module.Application()
        app.tray_icon = MagicMock()
        app.logic_engine = MagicMock()
        app.logic_engine.get_mode.return_value = "active" # Mimic current behavior trigger

        # Act
        app.on_feedback_helpful_pressed()

        # Assert
        # We expect it to be called with "feedback_helpful"
        app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_helpful",
            duration=0.3,
            flashes=1
        )

    def test_feedback_unhelpful_flash(self):
        # Setup
        app = self.main_module.Application()
        app.tray_icon = MagicMock()
        app.logic_engine = MagicMock()
        app.logic_engine.get_mode.return_value = "active"

        # Act
        app.on_feedback_unhelpful_pressed()

        # Assert
        app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_unhelpful",
            duration=0.3,
            flashes=1
        )
