import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main
import config

class TestEcoMode(unittest.TestCase):
    def setUp(self):
        # Patch dependencies that main.Application needs
        self.patchers = []

        self.mock_logger = MagicMock()
        self.patchers.append(patch('main.DataLogger', return_value=self.mock_logger))
        self.patchers.append(patch('main.VideoSensor', return_value=MagicMock()))
        self.patchers.append(patch('main.AudioSensor', return_value=MagicMock()))
        self.patchers.append(patch('main.LMMInterface', return_value=MagicMock()))
        self.patchers.append(patch('main.LogicEngine')) # We will configure instance later
        self.patchers.append(patch('main.InterventionEngine', return_value=MagicMock()))
        self.patchers.append(patch('main.ACRTrayIcon', return_value=MagicMock()))

        # Start patches
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_get_video_poll_delay(self):
        # Initialize app
        # This triggers __init__, which uses the mocked classes
        app = main.Application()

        # Verify LogicEngine was mocked
        self.assertTrue(isinstance(app.logic_engine, MagicMock))

        # Set config values for test
        # We need to patch main.config because main.py imports config
        with patch.object(main.config, 'VIDEO_ACTIVE_DELAY', 0.05), \
             patch.object(main.config, 'VIDEO_ECO_MODE_DELAY', 1.0):

            # Case 1: Face Detected -> Active Delay
            app.logic_engine.is_face_detected.return_value = True
            delay = app._get_video_poll_delay()
            self.assertEqual(delay, 0.05, "Should return active delay when face is detected")

            # Case 2: No Face -> Eco Mode Delay
            app.logic_engine.is_face_detected.return_value = False
            delay = app._get_video_poll_delay()
            self.assertEqual(delay, 1.0, "Should return eco mode delay when no face is detected")

if __name__ == '__main__':
    unittest.main()
