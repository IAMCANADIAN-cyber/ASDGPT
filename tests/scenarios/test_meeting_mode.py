import unittest
from unittest.mock import MagicMock, patch
import time
import numpy as np
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface

class TestMeetingMode(unittest.TestCase):
    def setUp(self):
        self.mock_lmm = MagicMock(spec=LMMInterface)
        self.mock_audio_sensor = MagicMock()
        self.mock_video_sensor = MagicMock()

        self.logic_engine = LogicEngine(
            audio_sensor=self.mock_audio_sensor,
            video_sensor=self.mock_video_sensor,
            lmm_interface=self.mock_lmm
        )

        # Default mock returns
        self.mock_audio_sensor.analyze_chunk.return_value = {"rms": 0.0, "is_speech": False}
        self.mock_video_sensor.process_frame.return_value = {"face_detected": False}

        # Suppress logging to keep output clean
        self.logic_engine.logger.log_info = MagicMock()
        self.logic_engine.logger.log_debug = MagicMock()

    def test_meeting_mode_trigger_and_exit(self):
        print("\nTest: Meeting Mode Trigger & Exit")

        # 1. Start in Active mode
        self.logic_engine.set_mode("active")
        self.assertEqual(self.logic_engine.get_mode(), "active")

        # Setup start time
        start_time = 1000.0

        # Helper to simulate an update cycle at a specific time
        def run_update(current_time, is_speech, face_detected):
            with patch('time.time', return_value=current_time):
                # Update inputs
                self.mock_audio_sensor.analyze_chunk.return_value = {"is_speech": is_speech}
                self.mock_video_sensor.process_frame.return_value = {"face_detected": face_detected}

                # Push data
                self.logic_engine.process_audio_data(np.zeros(100))
                self.logic_engine.process_video_data(np.zeros((100,100,3)))

                self.logic_engine.update()

        # Step 1: Initialize Idle state (User hasn't touched keyboard for > 10s)
        # logic_engine.last_user_input_time is initialized to time.time() in __init__
        # We need to force it to be old.
        self.logic_engine.last_user_input_time = start_time - 20.0 # 20s ago

        # Step 2: Speech starts (Face detected)
        # Time: start_time
        run_update(start_time, is_speech=True, face_detected=True)
        self.assertEqual(self.logic_engine.get_mode(), "active") # Not yet 3s speech

        # Step 3: Speech continues for 2.9s
        run_update(start_time + 2.9, is_speech=True, face_detected=True)
        self.assertEqual(self.logic_engine.get_mode(), "active")

        # Step 4: Speech continues for 3.1s -> Should Trigger
        run_update(start_time + 3.1, is_speech=True, face_detected=True)
        self.assertEqual(self.logic_engine.get_mode(), "dnd")
        self.assertTrue(self.logic_engine.auto_dnd_active)
        print("Meeting Mode Triggered successfully.")

        # Step 5: User Input occurs
        # register_user_input uses time.time(), so we must patch it there too
        with patch('time.time', return_value=start_time + 10.0):
            self.logic_engine.register_user_input()

        # Step 6: Verify Auto-Exit
        self.assertEqual(self.logic_engine.get_mode(), "active")
        self.assertFalse(self.logic_engine.auto_dnd_active)
        print("Auto-Exit verified.")

    def test_meeting_mode_no_trigger_if_not_idle(self):
        print("\nTest: Meeting Mode No Trigger (Not Idle)")
        self.logic_engine.set_mode("active")
        start_time = 2000.0

        # User input recently
        self.logic_engine.last_user_input_time = start_time - 2.0

        def run_update(current_time, is_speech, face_detected):
            with patch('time.time', return_value=current_time):
                self.mock_audio_sensor.analyze_chunk.return_value = {"is_speech": is_speech}
                self.mock_video_sensor.process_frame.return_value = {"face_detected": face_detected}
                self.logic_engine.process_audio_data(np.zeros(100))
                self.logic_engine.process_video_data(np.zeros((100,100,3)))
                self.logic_engine.update()

        # Speech > 3s, Face Detected, BUT NOT IDLE
        run_update(start_time, True, True)
        run_update(start_time + 4.0, True, True)

        self.assertEqual(self.logic_engine.get_mode(), "active")
        self.assertFalse(self.logic_engine.auto_dnd_active)
        print("Meeting Mode correctly suppressed due to user activity.")

    def test_meeting_mode_no_trigger_if_no_face(self):
        print("\nTest: Meeting Mode No Trigger (No Face)")
        self.logic_engine.set_mode("active")
        start_time = 3000.0
        self.logic_engine.last_user_input_time = start_time - 20.0

        def run_update(current_time, is_speech, face_detected):
            with patch('time.time', return_value=current_time):
                self.mock_audio_sensor.analyze_chunk.return_value = {"is_speech": is_speech}
                self.mock_video_sensor.process_frame.return_value = {"face_detected": face_detected}
                self.logic_engine.process_audio_data(np.zeros(100))
                self.logic_engine.process_video_data(np.zeros((100,100,3)))
                self.logic_engine.update()

        # Speech > 3s, Idle, BUT NO FACE
        run_update(start_time, True, False)
        run_update(start_time + 4.0, True, False)

        self.assertEqual(self.logic_engine.get_mode(), "active")
        print("Meeting Mode correctly suppressed due to missing face.")

if __name__ == '__main__':
    unittest.main()
