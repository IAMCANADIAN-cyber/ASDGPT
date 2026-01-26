import unittest
from unittest.mock import MagicMock, patch
import sys
import importlib

class TestMainFeedbackCalls(unittest.TestCase):
    def setUp(self):
        # 1. Patch sys.modules to mock heavy dependencies BEFORE importing main
        self.modules_patcher = patch.dict(sys.modules, {
            "sounddevice": MagicMock(),
            "cv2": MagicMock(),
            "pystray": MagicMock(),
            "PIL": MagicMock(),
            "PIL.Image": MagicMock(),
            "keyboard": MagicMock(),
            "requests": MagicMock(),
            "numpy": MagicMock(),
            # Mock internal modules that main imports
            "core.logic_engine": MagicMock(),
            "core.intervention_engine": MagicMock(),
            "core.system_tray": MagicMock(),
            "core.data_logger": MagicMock(),
            "core.lmm_interface": MagicMock(),
            "sensors.video_sensor": MagicMock(),
            "sensors.audio_sensor": MagicMock(),
        })
        self.modules_patcher.start()

        # 2. Import main (which will use the mocks)
        import main
        importlib.reload(main) # Ensure we get a fresh version
        self.main_module = main

        # 3. Setup the Application instance
        # We need to mock the components that Application.__init__ instantiates

        # Mock DataLogger
        self.mock_logger = MagicMock()
        self.main_module.DataLogger.return_value = self.mock_logger

        # Mock Sensors
        self.mock_video = MagicMock()
        self.main_module.VideoSensor.return_value = self.mock_video
        self.mock_audio = MagicMock()
        self.main_module.AudioSensor.return_value = self.mock_audio

        # Mock Engines
        self.mock_logic = MagicMock()
        self.main_module.LogicEngine.return_value = self.mock_logic
        self.mock_intervention = MagicMock()
        self.main_module.InterventionEngine.return_value = self.mock_intervention

        # Mock Tray
        self.mock_tray = MagicMock()
        self.main_module.ACRTrayIcon.return_value = self.mock_tray

        # Instantiate App
        self.app = self.main_module.Application()

    def tearDown(self):
        self.modules_patcher.stop()

    def test_helpful_feedback_visuals(self):
        """Test that helpful feedback triggers the correct icon flash."""
        # Setup: LogicEngine returns a mode (e.g. "active")
        self.app.logic_engine.get_mode.return_value = "active"

        # Action
        self.app.on_feedback_helpful_pressed()

        # Assertions
        # 1. Intervention Engine registered feedback
        self.app.intervention_engine.register_feedback.assert_called_with("helpful")

        # 2. Tray Icon flashed correctly
        # EXPECTATION: It should use 'feedback_helpful', NOT 'active'
        self.app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_helpful",
            duration=0.3,
            flashes=1
        )

    def test_unhelpful_feedback_visuals(self):
        """Test that unhelpful feedback triggers the correct icon flash."""
        self.app.logic_engine.get_mode.return_value = "active"

        self.app.on_feedback_unhelpful_pressed()

        self.app.intervention_engine.register_feedback.assert_called_with("unhelpful")

        self.app.tray_icon.flash_icon.assert_called_with(
            flash_status="feedback_unhelpful",
            duration=0.3,
            flashes=1
        )

if __name__ == '__main__':
    unittest.main()
