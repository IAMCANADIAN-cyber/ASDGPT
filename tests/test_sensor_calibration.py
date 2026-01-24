import unittest
from unittest.mock import MagicMock, patch, ANY
import numpy as np
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sensors.audio_sensor import AudioSensor
from sensors.video_sensor import VideoSensor
# We don't import config directly for patching, we target where it is used.

class TestSensorCalibration(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()

    @patch('sensors.audio_sensor.sd.InputStream')
    def test_audio_calibration(self, mock_stream_cls):
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream

        # Chunks
        chunk1 = np.full(100, 0.01) # Cleared
        chunk2 = np.full(100, 0.02) # Recorded
        chunk3 = np.full(100, 0.015) # Recorded
        chunk4 = np.full(100, 0.01) # Recorded?

        sensor = AudioSensor(data_logger=self.mock_logger)

        # Time strategy:
        # Start: 0
        # Clear buffer (get_chunk)
        # Loop 1 check: 0 < 0.3? Yes.
        #   get_chunk (chunk2)
        #   sleep -> time becomes 0.1
        # Loop 2 check: 0.1 < 0.3? Yes.
        #   get_chunk (chunk3)
        #   sleep -> time becomes 0.2
        # Loop 3 check: 0.2 < 0.3? Yes.
        #   get_chunk (chunk4)
        #   sleep -> time becomes 0.3
        # Loop 4 check: 0.3 < 0.3? No. Exit.

        # So we need 4 chunks total (1 cleared + 3 recorded).
        # And time side effects: [0, 0.1, 0.2, 0.3, 0.4] (calls to time.time() inside loop + sleep?)
        # Actually time.time() is called in loop condition.
        # 1. Start: time.time() -> 0
        # 2. Loop cond: time.time() -> 0. (0-0 < 0.3)
        # 3. get_chunk
        # 4. time.sleep (mocked) -> need to increment time manually if we rely on side_effects or just supply sequence.

        # Simplified: We patch time.time to return sequence that controls loop
        # Calls:
        # 1. start_time = time.time()
        # 2. while time.time() - start ...
        # 3. while time.time() - start ... (after loop 1)
        # ...

        time_values = [
            0,    # start_time
            0.05, # loop 1 check (0.05 < 0.3)
            0.15, # loop 2 check (0.15 < 0.3)
            0.25, # loop 3 check (0.25 < 0.3)
            0.35  # loop 4 check (0.35 > 0.3) -> Exit
        ]

        with patch.object(sensor, 'get_chunk', side_effect=[
            (chunk1, None), # Buffer clear
            (chunk2, None), # Loop 1
            (chunk3, None), # Loop 2
            (chunk4, None), # Loop 3
            (None, None)
        ]):
            with patch('time.time', side_effect=time_values):
                 with patch('time.sleep'):
                     threshold = sensor.calibrate(duration=0.3)

        # Recorded: 0.02, 0.015, 0.01
        # Mean: (0.02+0.015+0.01)/3 = 0.045/3 = 0.015
        # Std (numpy population):
        #   Means: 0.015
        #   Diffs: 0.005, 0.0, -0.005
        #   Sq: 2.5e-5, 0, 2.5e-5
        #   Sum: 5.0e-5
        #   Mean Sq: 1.66e-5
        #   Std: 0.004082

        # Threshold: Mean + 4*Std = 0.015 + 4(0.004082) = 0.015 + 0.01633 = 0.03133
        # Max * 1.2 = 0.02 * 1.2 = 0.024

        self.assertAlmostEqual(threshold, 0.03133, places=4)

    @patch('sensors.video_sensor.cv2.VideoCapture')
    def test_video_calibration(self, mock_cap_cls):
        mock_cap = MagicMock()
        mock_cap_cls.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((100, 100, 3), dtype=np.uint8))

        sensor = VideoSensor(data_logger=self.mock_logger)

        metrics1 = {"face_detected": True, "face_roll_angle": 10, "face_size_ratio": 0.2, "vertical_position": 0.5, "horizontal_position": 0.5}
        metrics2 = {"face_detected": True, "face_roll_angle": 20, "face_size_ratio": 0.4, "vertical_position": 0.3, "horizontal_position": 0.5}

        # Loop control similar to above. 2 frames recorded.
        time_values = [0, 0.05, 0.15, 0.35] # Start, Loop 1, Loop 2, Exit

        with patch.object(sensor, 'process_frame', side_effect=[metrics1, metrics2]):
             with patch.object(sensor, 'get_frame', return_value=(np.zeros((100,100,3)), None)):
                 with patch('time.time', side_effect=time_values):
                     with patch('time.sleep'):
                         baseline = sensor.calibrate(duration=0.3)

        self.assertAlmostEqual(baseline["face_roll_angle"], 15.0, places=4)
        self.assertAlmostEqual(baseline["face_size_ratio"], 0.3, places=4)
        self.assertAlmostEqual(baseline["vertical_position"], 0.4, places=4)

    def test_video_posture_logic_relative(self):
        sensor = VideoSensor(data_logger=self.mock_logger)

        custom_baseline = {
            "face_roll_angle": 10.0,
            "face_size_ratio": 0.3,
            "vertical_position": 0.4
        }

        # Must use create=True because config.BASELINE_POSTURE doesn't exist by default
        with patch('sensors.video_sensor.config.BASELINE_POSTURE', custom_baseline, create=True):
            metrics = {
                "face_detected": True,
                "face_roll_angle": 12.0,
                "face_size_ratio": 0.32,
                "vertical_position": 0.42
            }
            sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "neutral")

            metrics = {
                "face_detected": True,
                "face_roll_angle": 35.0,
                "face_size_ratio": 0.3,
                "vertical_position": 0.4
            }
            sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "tilted_right")

            metrics = {
                "face_detected": True,
                "face_roll_angle": 10.0,
                "face_size_ratio": 0.4,
                "vertical_position": 0.4
            }
            sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "leaning_forward")

    def test_video_posture_logic_fallback(self):
        sensor = VideoSensor(data_logger=self.mock_logger)

        with patch('sensors.video_sensor.config.BASELINE_POSTURE', {}, create=True):
            metrics = {"face_detected": True, "face_size_ratio": 0.5, "vertical_position": 0.4}
            sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "leaning_forward")

            metrics = {"face_detected": True, "face_size_ratio": 0.3, "vertical_position": 0.7}
            sensor._calculate_posture(metrics)
            self.assertEqual(metrics["posture_state"], "slouching")

if __name__ == '__main__':
    unittest.main()
