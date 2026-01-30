import unittest
from unittest.mock import MagicMock, patch
import sys
import config

class TestVideoEcoMode(unittest.TestCase):
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

        # Import main after patching
        if 'main' in sys.modules:
            del sys.modules['main']
        import main
        self.main_module = main

        # Save config
        self.original_eco_enabled = config.VIDEO_ECO_MODE_ENABLED
        self.original_eco_fps = config.VIDEO_ECO_FPS_DELAY

    def tearDown(self):
        self.modules_patcher.stop()
        config.VIDEO_ECO_MODE_ENABLED = self.original_eco_enabled
        config.VIDEO_ECO_FPS_DELAY = self.original_eco_fps

    def test_calculate_interval_eco_disabled(self):
        """Should return base interval if Eco Mode is disabled."""
        config.VIDEO_ECO_MODE_ENABLED = False

        app = self.main_module.Application()
        app.logic_engine = MagicMock()
        # Even if no face detected
        app.logic_engine.face_metrics = {"face_detected": False}

        interval = app._calculate_video_poll_interval()
        self.assertEqual(interval, 0.05)

    def test_calculate_interval_face_detected(self):
        """Should return base interval if Face is detected (regardless of Eco Mode)."""
        config.VIDEO_ECO_MODE_ENABLED = True

        app = self.main_module.Application()
        app.logic_engine = MagicMock()
        app.logic_engine.face_metrics = {"face_detected": True}

        interval = app._calculate_video_poll_interval()
        self.assertEqual(interval, 0.05)

    def test_calculate_interval_eco_active_no_face(self):
        """Should return ECO delay if Eco Mode is enabled and No Face detected."""
        config.VIDEO_ECO_MODE_ENABLED = True
        config.VIDEO_ECO_FPS_DELAY = 1.5 # Custom delay

        app = self.main_module.Application()
        app.logic_engine = MagicMock()
        app.logic_engine.face_metrics = {"face_detected": False}

        interval = app._calculate_video_poll_interval()
        self.assertEqual(interval, 1.5)

if __name__ == '__main__':
    unittest.main()
