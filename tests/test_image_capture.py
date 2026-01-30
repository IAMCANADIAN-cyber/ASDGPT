import unittest
import os
import shutil
import time
from unittest.mock import MagicMock, patch
import numpy as np
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from sensors.video_sensor import VideoSensor
from core.intervention_engine import InterventionEngine
from core.logic_engine import LogicEngine
import config

class TestImageCapture(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join("tests", "temp_images")
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

        # Mock LogicEngine and Logger
        self.mock_logger = MagicMock()
        self.mock_logic = MagicMock()

        # We need to mock cv2.imwrite inside VideoSensor
        self.cv2_patcher = patch('cv2.imwrite')
        self.mock_imwrite = self.cv2_patcher.start()
        self.mock_imwrite.return_value = True

        # Mock VideoCapture
        self.cap_patcher = patch('cv2.VideoCapture')
        self.mock_cap_cls = self.cap_patcher.start()
        self.mock_cap = MagicMock()
        self.mock_cap.isOpened.return_value = True
        self.mock_cap.read.return_value = (True, np.zeros((100, 100, 3), dtype=np.uint8))
        self.mock_cap_cls.return_value = self.mock_cap

        self.sensor = VideoSensor(camera_index=0, data_logger=self.mock_logger)
        self.mock_logic.video_sensor = self.sensor

        self.intervention_engine = InterventionEngine(logic_engine=self.mock_logic)

    def tearDown(self):
        self.cv2_patcher.stop()
        self.cap_patcher.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_video_sensor_save_snapshot(self):
        """Test that VideoSensor has a save_snapshot method that calls cv2.imwrite"""
        filepath = os.path.join(self.test_dir, "test_snapshot.jpg")

        # Determine if method exists first
        if not hasattr(self.sensor, 'save_snapshot'):
            self.fail("VideoSensor missing save_snapshot method")

        success = self.sensor.save_snapshot(filepath)

        self.assertTrue(success)
        self.mock_imwrite.assert_called_once()
        args, _ = self.mock_imwrite.call_args
        self.assertEqual(args[0], filepath)

    def test_intervention_engine_capture_image(self):
        """Test that InterventionEngine._capture_image calls VideoSensor.save_snapshot"""

        # Mock save_snapshot on the sensor instance attached to logic_engine
        self.sensor.save_snapshot = MagicMock(return_value=True)

        details = "test_selfie"
        # We access the private method directly for unit testing
        self.intervention_engine._capture_image(details)

        self.sensor.save_snapshot.assert_called_once()
        args, _ = self.sensor.save_snapshot.call_args
        # Check that filepath contains the details and follows expected structure
        saved_path = args[0]
        self.assertIn(details, saved_path)
        self.assertIn("captured_images", saved_path)

if __name__ == '__main__':
    unittest.main()
