import pytest
import unittest
from unittest.mock import MagicMock, patch
import config
from main import Application
import sys

class TestEcoMode(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_logic_engine = MagicMock()
        self.mock_video_sensor = MagicMock()
        self.mock_logger = MagicMock()

        # Patch dependencies before Application init
        self.patchers = []

        # Patch VideoSensor and AudioSensor classes
        p1 = patch('main.VideoSensor', return_value=self.mock_video_sensor)
        p2 = patch('main.AudioSensor', MagicMock())
        p3 = patch('main.LMMInterface', MagicMock())
        p4 = patch('main.LogicEngine', return_value=self.mock_logic_engine)
        p5 = patch('main.InterventionEngine', MagicMock())
        p6 = patch('main.ACRTrayIcon', MagicMock())
        p7 = patch('main.DataLogger', return_value=self.mock_logger)
        # Patch keyboard which is imported inside _setup_hotkeys
        p8 = patch.dict(sys.modules, {'keyboard': MagicMock()})

        self.patchers.extend([p1, p2, p3, p4, p5, p6, p7, p8])
        for p in self.patchers:
            p.start()

        # Initialize App
        self.app = Application()
        # Ensure our mock logic engine is attached
        self.app.logic_engine = self.mock_logic_engine

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        if self.app:
            self.app.quit_application()

    def test_get_video_poll_delay_idle_mode(self):
        """Test delay when not in active mode."""
        self.mock_logic_engine.get_mode.return_value = "paused"
        delay = self.app._get_video_poll_delay(activity=100.0)
        self.assertEqual(delay, 0.2)

    def test_get_video_poll_delay_face_detected(self):
        """Test delay when face is detected (should be active delay)."""
        self.mock_logic_engine.get_mode.return_value = "active"
        self.mock_logic_engine.is_face_detected.return_value = True

        delay = self.app._get_video_poll_delay(activity=0.0)
        self.assertEqual(delay, config.VIDEO_ACTIVE_DELAY)

    def test_get_video_poll_delay_high_activity(self):
        """Test delay when no face but high activity (should wake up)."""
        self.mock_logic_engine.get_mode.return_value = "active"
        self.mock_logic_engine.is_face_detected.return_value = False

        # Activity > VIDEO_WAKE_THRESHOLD (5.0)
        delay = self.app._get_video_poll_delay(activity=6.0)
        self.assertEqual(delay, config.VIDEO_ACTIVE_DELAY)

    def test_get_video_poll_delay_eco_mode(self):
        """Test delay when no face and low activity (should sleep)."""
        self.mock_logic_engine.get_mode.return_value = "active"
        self.mock_logic_engine.is_face_detected.return_value = False

        # Activity <= VIDEO_WAKE_THRESHOLD (5.0)
        delay = self.app._get_video_poll_delay(activity=4.0)
        self.assertEqual(delay, config.VIDEO_ECO_MODE_DELAY)
