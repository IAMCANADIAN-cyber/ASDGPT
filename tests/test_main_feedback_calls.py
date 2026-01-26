import unittest
from unittest.mock import MagicMock, patch
import sys
import importlib

class TestMainFeedbackCalls(unittest.TestCase):
    def setUp(self):
        # Patch sys.modules to mock heavy dependencies that main.py imports at top level
        self.modules_patcher = patch.dict(sys.modules, {
            "keyboard": MagicMock(),
            "sounddevice": MagicMock(),
            "pystray": MagicMock(),
            "cv2": MagicMock(),
            "PIL": MagicMock(),
            "PIL.Image": MagicMock(),
            "PIL.ImageDraw": MagicMock(),
            "numpy": MagicMock(),
            "requests": MagicMock(),
            "dotenv": MagicMock(),
            # We also need to mock our own modules if they import heavy stuff,
            # but main.py imports them. Let's let them load but mock the heavy stuff they use.
            # actually, main.py imports classes from core.* and sensors.*.
            # We can mock those classes in sys.modules or let them import mocked dependencies.
            # Given the structure, it's safer to mock the external libs (as done above)
            # AND patch the classes main.py imports if we want to avoid their init logic.
        })
        self.modules_patcher.start()

        # We need to make sure config is available
        if "config" not in sys.modules:
             sys.modules["config"] = MagicMock()

        # Configure config mock with strings to avoid TypeError in DataLogger
        sys.modules["config"].LOG_LEVEL = "INFO"
        sys.modules["config"].LOG_FILE = "test_log.log"
        sys.modules["config"].EVENTS_FILE = "test_events.jsonl"
        sys.modules["config"].LOG_MAX_BYTES = 1024
        sys.modules["config"].LOG_BACKUP_COUNT = 1
        sys.modules["config"].HOTKEY_FEEDBACK_HELPFUL = "h"
        sys.modules["config"].HOTKEY_FEEDBACK_UNHELPFUL = "u"
        sys.modules["config"].CAMERA_INDEX = 0
        sys.modules["config"].FEEDBACK_WINDOW_SECONDS = 15
        sys.modules["config"].SNOOZE_DURATION = 3600
        sys.modules["config"].APP_NAME = "ASDGPT"

        # Reload main to apply patches
        import main
        importlib.reload(main)
        self.main_module = main

        # Create an instance of Application
        # We need to mock the constructor's internal calls to sensors/loggers to avoid side effects
        with patch('core.data_logger.DataLogger') as mock_logger, \
             patch('sensors.video_sensor.VideoSensor') as mock_video, \
             patch('sensors.audio_sensor.AudioSensor') as mock_audio, \
             patch('core.lmm_interface.LMMInterface') as mock_lmm, \
             patch('core.logic_engine.LogicEngine') as mock_logic, \
             patch('core.intervention_engine.InterventionEngine') as mock_intervention, \
             patch('core.system_tray.ACRTrayIcon') as mock_tray:

            self.app = self.main_module.Application()

            # Re-attach mocks to the instance so we can inspect them
            self.app.data_logger = mock_logger.return_value
            self.app.video_sensor = mock_video.return_value
            self.app.audio_sensor = mock_audio.return_value
            self.app.lmm_interface = mock_lmm.return_value
            self.app.logic_engine = mock_logic.return_value
            self.app.intervention_engine = mock_intervention.return_value
            self.app.tray_icon = mock_tray.return_value

            # LogicEngine mock needs get_mode to return something valid
            self.app.logic_engine.get_mode.return_value = "active"

    def tearDown(self):
        self.modules_patcher.stop()

    def test_feedback_helpful_visual(self):
        """Test that helpful feedback triggers green flash."""
        self.app.on_feedback_helpful_pressed()

        # Verify intervention engine was notified
        self.app.intervention_engine.register_feedback.assert_called_with("helpful")

        # Verify tray icon flash called with CORRECT status
        # This is expected to FAIL initially (will call with "active" instead of "feedback_helpful")
        self.app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_helpful",
            duration=0.3,
            flashes=1
        )

    def test_feedback_unhelpful_visual(self):
        """Test that unhelpful feedback triggers red flash."""
        self.app.on_feedback_unhelpful_pressed()

        self.app.intervention_engine.register_feedback.assert_called_with("unhelpful")

        # This is expected to FAIL initially
        self.app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_unhelpful",
            duration=0.3,
            flashes=1
        )

if __name__ == '__main__':
    unittest.main()
