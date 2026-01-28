import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import Application
from core.logic_engine import LogicEngine
import config

class TestEcoMode(unittest.TestCase):
    def setUp(self):
        # Mock dependencies for Application
        self.mock_logger = MagicMock()
        self.mock_video_sensor = MagicMock()
        self.mock_audio_sensor = MagicMock()
        self.mock_lmm_interface = MagicMock()
        self.mock_logic_engine = MagicMock()
        self.mock_intervention_engine = MagicMock()
        self.mock_tray_icon = MagicMock()

        # Patch heavy dependencies to prevent real initialization in main.py
        self.patches = [
            patch('main.DataLogger', return_value=self.mock_logger),
            patch('main.VideoSensor', return_value=self.mock_video_sensor),
            patch('main.AudioSensor', return_value=self.mock_audio_sensor),
            patch('main.LMMInterface', return_value=self.mock_lmm_interface),
            # We patch LogicEngine class in main, so Application() gets a mock
            patch('main.LogicEngine', return_value=self.mock_logic_engine),
            patch('main.InterventionEngine', return_value=self.mock_intervention_engine),
            patch('main.ACRTrayIcon', return_value=self.mock_tray_icon),
        ]

        # Patch keyboard module globally since it's imported inside a method
        self.keyboard_patch = patch.dict(sys.modules, {'keyboard': MagicMock()})
        self.keyboard_patch.start()

        for p in self.patches:
            p.start()

        # Initialize app with mocks
        self.app = Application()
        # Explicitly set the logic engine mock (though constructor does it via return_value)
        self.app.logic_engine = self.mock_logic_engine

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.keyboard_patch.stop()

    def test_poll_delay_not_active(self):
        """Test delay when mode is not active."""
        self.mock_logic_engine.get_mode.return_value = "snoozed"
        delay = self.app._get_video_poll_delay()
        self.assertEqual(delay, 0.2)

    def test_poll_delay_active_face_detected(self):
        """Test delay when active and face detected."""
        self.mock_logic_engine.get_mode.return_value = "active"
        self.mock_logic_engine.is_face_detected.return_value = True

        # Ensure we test against the expected constant value
        expected_delay = getattr(config, 'VIDEO_ACTIVE_DELAY', 0.05)
        delay = self.app._get_video_poll_delay()
        self.assertEqual(delay, expected_delay)

    def test_poll_delay_active_no_face(self):
        """Test delay when active and NO face detected (Eco Mode)."""
        self.mock_logic_engine.get_mode.return_value = "active"
        self.mock_logic_engine.is_face_detected.return_value = False

        expected_delay = getattr(config, 'VIDEO_ECO_MODE_DELAY', 1.0)
        delay = self.app._get_video_poll_delay()
        self.assertEqual(delay, expected_delay)

class TestLogicEngineEcoSupport(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()
        self.mock_lmm = MagicMock()
        # Instantiate real LogicEngine but with mock dependencies
        self.le = LogicEngine(self.mock_audio, self.mock_video, self.mock_logger, self.mock_lmm)

    def test_is_face_detected_accessor(self):
        """Verify thread-safe accessor works with internal state."""
        # Initial state
        self.assertFalse(self.le.is_face_detected())

        # Modify internal state directly
        with self.le._lock:
            self.le.face_metrics["face_detected"] = True

        self.assertTrue(self.le.is_face_detected())

        with self.le._lock:
            self.le.face_metrics["face_detected"] = False

        self.assertFalse(self.le.is_face_detected())

if __name__ == '__main__':
    unittest.main()
