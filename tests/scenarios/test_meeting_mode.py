import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.logic_engine import LogicEngine
from core.state_engine import StateEngine
from core.data_logger import DataLogger
import config

# Mocks (simplified from ReplayHarness)
class MockLMMInterface:
    def __init__(self):
        self.last_analysis = {}
    def process_data(self, video_data=None, audio_data=None, user_context=None):
        return {} # dummy
    def get_intervention_suggestion(self, analysis):
        return None

class MockInterventionEngine:
    def __init__(self):
        self.triggered_interventions = []
    def start_intervention(self, suggestion):
        self.triggered_interventions.append(suggestion)
    def get_suppressed_intervention_types(self): return []
    def get_preferred_intervention_types(self): return []
    def notify_mode_change(self, mode, message=""): pass

class TestMeetingMode(unittest.TestCase):
    def setUp(self):
        self.logger = DataLogger("test_meeting_mode.log")
        self.mock_lmm = MockLMMInterface()
        self.mock_audio = MagicMock()
        self.mock_video = MagicMock()

        # Setup LogicEngine
        self.logic_engine = LogicEngine(
            audio_sensor=self.mock_audio,
            video_sensor=self.mock_video,
            logger=self.logger,
            lmm_interface=self.mock_lmm
        )
        self.mock_ie = MockInterventionEngine()
        self.logic_engine.set_intervention_engine(self.mock_ie)

        # Configure Thresholds explicitly for test stability
        self.original_speech_duration = getattr(config, 'MEETING_SPEECH_DURATION', 5)
        config.MEETING_SPEECH_DURATION = 5
        config.MEETING_FACE_DURATION = 5
        config.MEETING_IDLE_DURATION = 5 # Shorten for test

    def tearDown(self):
        config.MEETING_SPEECH_DURATION = self.original_speech_duration

    def test_meeting_mode_trigger_and_exit(self):
        """
        Verifies that:
        1. Mode remains 'active' when conditions are not met.
        2. Mode switches to 'dnd' when Speech + Face + Idle > Thresholds.
        3. Mode switches back to 'active' when User Input occurs.
        """

        # Time Machine
        # Use a list to hold the mutable time variable so closure works
        time_state = {"current": 1000.0}

        def mock_time():
            return time_state["current"]

        # Patch time in logic_engine
        with patch('core.logic_engine.time.time', side_effect=mock_time):
            # Init state
            self.logic_engine.last_user_input_time = time_state["current"] # Reset idle
            self.logic_engine.current_mode = "active"

            # --- Step 1: Start (Active, No Speech, No Face) ---
            # Idle is 0.
            self.mock_audio.analyze_chunk.return_value = {"is_speech": False, "rms": 0.1}
            self.mock_video.process_frame.return_value = {"face_detected": False}

            self.logic_engine.process_audio_data(np.zeros(10))
            self.logic_engine.process_video_data(np.zeros((10,10,3)))
            self.logic_engine.update()

            self.assertEqual(self.logic_engine.get_mode(), "active")
            self.assertFalse(self.logic_engine.meeting_mode_active)

            # --- Step 2: Speech & Face Start ---
            # Advance time slightly
            time_state["current"] += 1.0
            # Idle = 1.0

            self.mock_audio.analyze_chunk.return_value = {"is_speech": True, "rms": 0.5}
            self.mock_video.process_frame.return_value = {"face_detected": True}

            self.logic_engine.process_audio_data(np.zeros(10))
            self.logic_engine.process_video_data(np.zeros((10,10,3)))
            self.logic_engine.update()

            # Should still be active (duration < 5)
            self.assertEqual(self.logic_engine.get_mode(), "active")

            # --- Step 3: Advance Time to Meet Thresholds ---
            # We need +5 seconds of CONTINUOUS speech/face.
            # And Idle > 5 (since we set config to 5).

            time_state["current"] += 6.0
            # Idle = 7.0 (> 5)
            # Speech/Face duration will be calculated relative to start time.
            # Note: LogicEngine logic checks duration from start_time.
            # We must ensure start_time was set in Step 2.
            # Step 2 set start_time = 1001.0.
            # Now time = 1007.0. Duration = 6.0 (> 5).

            self.logic_engine.process_audio_data(np.zeros(10))
            self.logic_engine.process_video_data(np.zeros((10,10,3)))
            self.logic_engine.update()

            self.assertEqual(self.logic_engine.get_mode(), "dnd", "Should switch to DND after duration thresholds met")
            self.assertTrue(self.logic_engine.meeting_mode_active)

            # --- Step 4: Exit via User Input ---
            # Simulate user typing
            # logic_engine.register_user_input() updates last_user_input_time to current_time.
            self.logic_engine.register_user_input()
            # Now Idle = 0.

            self.logic_engine.update()

            self.assertEqual(self.logic_engine.get_mode(), "active", "Should revert to active on user input")
            self.assertFalse(self.logic_engine.meeting_mode_active)

if __name__ == '__main__':
    unittest.main()
