import os
import sys
import pytest
from unittest.mock import MagicMock

# Setup path for headless testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine
from core.data_logger import DataLogger

class MockSensor:
    def __init__(self, activity=0.0, face_detected=True, face_count=1):
        self.activity = activity
        self.face_detected = face_detected
        self.face_count = face_count

    def process_frame(self, frame):
        return {
            "video_activity": self.activity,
            "face_detected": self.face_detected,
            "face_count": self.face_count,
            "posture_state": "slouching"
        }

@pytest.fixture
def logic_engine():
    logger = MagicMock(spec=DataLogger)
    engine = LogicEngine(logger=logger)
    # Give it a tiny LMM interval so we can trigger updates immediately
    engine.min_lmm_interval = 0
    engine.lmm_call_interval = 0

    # Mock video sensor
    engine.video_sensor = MockSensor()

    # Mock lmm_interface
    engine.lmm_interface = MagicMock()

    # Needs to process one frame to initialize last_video_frame
    import numpy as np
    dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    engine.process_video_data(dummy_frame)
    return engine

@pytest.fixture
def intervention_engine(logic_engine):
    ie = InterventionEngine(logic_engine=logic_engine)
    # Need to override some things that spawn threads
    ie._play_sound = MagicMock()
    ie._speak = MagicMock()
    ie._show_system_alert = MagicMock()
    return ie

def test_gaming_mode_ignores_high_activity(logic_engine, intervention_engine):
    """
    Verify that when in gaming mode, high video activity doesn't trigger LMM.
    """
    logic_engine.set_intervention_engine(intervention_engine)
    logic_engine.set_mode("gaming")

    # Set high video activity
    logic_engine.video_sensor.activity = 100.0  # High activity
    logic_engine.video_activity_threshold_high = 20.0

    # Process a frame to update metrics
    import numpy as np
    dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    logic_engine.process_video_data(dummy_frame)

    # Update logic engine
    logic_engine.update()

    # Should not trigger LMM for high_video_activity
    # Verify that trigger_reason 'high_video_activity' wasn't used to call LMM
    calls = logic_engine.logger.log_event.call_args_list
    lmm_triggers = [call for call in calls if call[0][0] == 'lmm_trigger']

    if lmm_triggers:
        assert lmm_triggers[-1][0][1]['reason'] != 'high_video_activity'


def test_gaming_mode_allows_posture_intervention(logic_engine, intervention_engine):
    """
    Verify that in gaming mode, posture interventions are allowed.
    """
    logic_engine.set_intervention_engine(intervention_engine)
    logic_engine.set_mode("gaming")

    # Ensure no global cooldown blocks it
    intervention_engine.last_intervention_time = 0

    # Start a posture intervention
    payload = {
        "id": "posture_water_reset",
        "type": "posture_water_reset",
        "tier": 1
    }

    success = intervention_engine.start_intervention(payload)

    assert success is True, "posture_water_reset should be allowed in gaming mode"


def test_gaming_mode_blocks_other_interventions(logic_engine, intervention_engine):
    """
    Verify that in gaming mode, non-posture interventions are blocked.
    """
    logic_engine.set_intervention_engine(intervention_engine)
    logic_engine.set_mode("gaming")

    # Start a distraction intervention
    payload = {
        "id": "distraction_alert",
        "type": "distraction_alert",
        "tier": 1
    }

    success = intervention_engine.start_intervention(payload)

    assert success is False, "distraction_alert should be blocked in gaming mode"
