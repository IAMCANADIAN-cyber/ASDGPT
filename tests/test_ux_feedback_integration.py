import unittest
from unittest.mock import MagicMock, patch
import sys
import importlib

# Mock dependencies BEFORE importing main
sys.modules["sounddevice"] = MagicMock()
sys.modules["cv2"] = MagicMock()
sys.modules["pystray"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["PIL.ImageDraw"] = MagicMock()
sys.modules["keyboard"] = MagicMock()

# Now we can import main safely
import main

class TestUXFeedbackIntegration(unittest.TestCase):
    def setUp(self):
        # Patch config to avoid side effects
        self.config_patcher = patch("main.config")
        self.mock_config = self.config_patcher.start()

        # Patch DataLogger to avoid file creation
        self.logger_patcher = patch("main.DataLogger")
        self.mock_logger_cls = self.logger_patcher.start()
        self.mock_logger = self.mock_logger_cls.return_value

        # Patch VideoSensor and AudioSensor to avoid initialization logic
        self.video_sensor_patcher = patch("main.VideoSensor")
        self.mock_video_sensor = self.video_sensor_patcher.start()

        self.audio_sensor_patcher = patch("main.AudioSensor")
        self.mock_audio_sensor = self.audio_sensor_patcher.start()

        # Patch LogicEngine and InterventionEngine
        self.logic_engine_patcher = patch("main.LogicEngine")
        self.mock_logic_engine = self.logic_engine_patcher.start().return_value

        self.intervention_engine_patcher = patch("main.InterventionEngine")
        self.mock_intervention_engine = self.intervention_engine_patcher.start().return_value

        # Patch TrayIcon
        self.tray_icon_patcher = patch("main.ACRTrayIcon")
        self.mock_tray_icon_cls = self.tray_icon_patcher.start()
        self.mock_tray_icon = self.mock_tray_icon_cls.return_value

        # Initialize App
        self.app = main.Application()
        # Inject mocks that might have been overwritten by init
        self.app.tray_icon = self.mock_tray_icon
        self.app.logic_engine = self.mock_logic_engine
        self.app.intervention_engine = self.mock_intervention_engine

    def tearDown(self):
        self.config_patcher.stop()
        self.logger_patcher.stop()
        self.video_sensor_patcher.stop()
        self.audio_sensor_patcher.stop()
        self.logic_engine_patcher.stop()
        self.intervention_engine_patcher.stop()
        self.tray_icon_patcher.stop()

    def test_helpful_feedback_flash(self):
        """Test that helpful feedback triggers specific green flash."""
        # Setup: LogicEngine returns "active"
        self.mock_logic_engine.get_mode.return_value = "active"

        # Action
        self.app.on_feedback_helpful_pressed()

        # Assert
        # CURRENT BUG: It calls with get_mode() result ("active")
        # DESIRED BEHAVIOR: Calls with "feedback_helpful"
        self.mock_tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_helpful",
            duration=0.3,
            flashes=1
        )

    def test_unhelpful_feedback_flash(self):
        """Test that unhelpful feedback triggers specific red flash."""
        # Setup
        self.mock_logic_engine.get_mode.return_value = "active"

        # Action
        self.app.on_feedback_unhelpful_pressed()

        # Assert
        # CURRENT BUG: It calls with get_mode() result ("active")
        # DESIRED BEHAVIOR: Calls with "feedback_unhelpful"
        self.mock_tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_unhelpful",
            duration=0.3,
            flashes=1
        )

if __name__ == "__main__":
    unittest.main()
