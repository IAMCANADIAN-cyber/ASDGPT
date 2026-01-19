import unittest
import sys
import os
import numpy as np
from unittest.mock import MagicMock, patch
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
import config

class TestMeetingMode(unittest.TestCase):
    def test_meeting_mode_trigger(self):
        """
        Verifies that Meeting Mode triggers DND when:
        1. Speech duration > threshold
        2. Face duration > threshold
        3. User Input idle > threshold
        """

        # Override config thresholds for predictability in test
        config.MEETING_MODE_SPEECH_DURATION = 10
        config.MEETING_MODE_FACE_DURATION = 10
        config.MEETING_MODE_NO_INPUT_DURATION = 10

        start_time = 10000.0

        # Patch time.time used by LogicEngine
        with patch('time.time') as mock_time:
            mock_time.return_value = start_time

            harness = ReplayHarness()
            # Ensure we start in active mode
            harness.logic_engine.set_mode("active")

            # --- Step 1: Start Activity (t=0) ---
            print("Step 1: Start Activity (t=0)")
            analysis = {
                "audio": {"is_speech": True, "speech_confidence": 0.8, "rms": 0.5},
                "video": {"face_detected": True, "video_activity": 30.0}
            }

            harness.mock_audio_sensor.analysis_result = analysis['audio']
            harness.mock_video_sensor.analysis_result = analysis['video']

            # Inject Data
            harness.logic_engine.process_video_data(np.zeros((100,100,3), dtype=np.uint8))
            harness.logic_engine.process_audio_data(np.full(1024, 0.5))
            harness.logic_engine.notify_user_input() # User just typed

            harness.logic_engine.update()

            self.assertEqual(harness.logic_engine.get_mode(), "active")
            self.assertTrue(harness.logic_engine.is_speaking)
            self.assertTrue(harness.logic_engine.is_face_present)
            self.assertEqual(harness.logic_engine.speech_start_time, start_time)

            # --- Step 2: 5 Seconds Later (t=5) ---
            print("Step 2: 5 Seconds Later (t=5)")
            mock_time.return_value = start_time + 5.0

            # User types again at t=5
            harness.logic_engine.notify_user_input()

            # LogicEngine update with same sensor data (continuous speech/face)
            harness.logic_engine.process_video_data(np.zeros((100,100,3), dtype=np.uint8))
            harness.logic_engine.process_audio_data(np.full(1024, 0.5))
            harness.logic_engine.update()

            self.assertEqual(harness.logic_engine.get_mode(), "active")

            # --- Step 3: 11 Seconds Later (t=11) ---
            print("Step 3: 11 Seconds Later (t=11)")
            mock_time.return_value = start_time + 11.0

            # User last typed at t=5. Idle = 6s. Threshold = 10s.
            # Speech/Face started at t=0. Duration = 11s. Threshold = 10s.
            # Conditions met: Speech, Face. Condition failed: Input Idle.

            harness.logic_engine.process_video_data(np.zeros((100,100,3), dtype=np.uint8))
            harness.logic_engine.process_audio_data(np.full(1024, 0.5))
            harness.logic_engine.update()

            self.assertEqual(harness.logic_engine.get_mode(), "active")

            # --- Step 4: 16 Seconds Later (t=16) ---
            print("Step 4: 16 Seconds Later (t=16)")
            mock_time.return_value = start_time + 16.0

            # User last typed at t=5. Idle = 11s. (>10s)
            # Speech/Face duration = 16s. (>10s)
            # All conditions met.

            harness.logic_engine.process_video_data(np.zeros((100,100,3), dtype=np.uint8))
            harness.logic_engine.process_audio_data(np.full(1024, 0.5))
            harness.logic_engine.update()

            self.assertEqual(harness.logic_engine.get_mode(), "dnd")
            print("Meeting Mode Successfully Triggered DND")

if __name__ == '__main__':
    unittest.main()
