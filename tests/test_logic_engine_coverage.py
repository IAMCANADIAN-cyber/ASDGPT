import pytest
from unittest.mock import MagicMock, patch, ANY
import numpy as np
import threading
import time
import sys

# Mock config before imports
sys.modules['config'] = MagicMock()
sys.modules['config'].DEFAULT_MODE = "active"
sys.modules['config'].AUDIO_THRESHOLD_HIGH = 0.5
sys.modules['config'].VIDEO_ACTIVITY_THRESHOLD_HIGH = 10.0
sys.modules['config'].LMM_CIRCUIT_BREAKER_MAX_FAILURES = 3
sys.modules['config'].LMM_CIRCUIT_BREAKER_COOLDOWN = 10
sys.modules['config'].SNOOZE_DURATION = 60
sys.modules['config'].DOOM_SCROLL_THRESHOLD = 3
sys.modules['config'].LOG_FILE = "test.log"
sys.modules['config'].EVENTS_FILE = "events.jsonl"
sys.modules['config'].LOG_MAX_BYTES = 1024
sys.modules['config'].LOG_BACKUP_COUNT = 1
sys.modules['config'].LOG_LEVEL = "INFO"

from core.logic_engine import LogicEngine

class TestLogicEngineCoverage:
    @pytest.fixture
    def mock_lmm(self):
        lmm = MagicMock()
        lmm.process_data.return_value = {"state_estimation": {}, "suggestion": None}
        return lmm

    @pytest.fixture
    def mock_intervention_engine(self):
        ie = MagicMock()
        ie.get_suppressed_intervention_types.return_value = []
        ie.get_preferred_intervention_types.return_value = []
        return ie

    @pytest.fixture
    def logic_engine(self, mock_lmm, mock_intervention_engine):
        # We need to mock DataLogger inside logic_engine init or handle its dependencies
        with patch('core.logic_engine.DataLogger') as MockLogger, \
             patch('core.logic_engine.StateEngine') as MockStateEngine:

            # Setup Mock State Engine
            mock_se = MockStateEngine.return_value
            mock_se.get_state.return_value = {"arousal": 50}

            engine = LogicEngine(lmm_interface=mock_lmm)
            engine.set_intervention_engine(mock_intervention_engine)
            return engine

    def test_init(self, logic_engine):
        assert logic_engine.current_mode == "active"
        assert logic_engine.lmm_interface is not None
        assert logic_engine.intervention_engine is not None

    def test_set_mode(self, logic_engine):
        logic_engine.set_mode("paused")
        assert logic_engine.current_mode == "paused"

        logic_engine.set_mode("snoozed")
        assert logic_engine.current_mode == "snoozed"
        assert logic_engine.snooze_end_time > 0

        logic_engine.set_mode("invalid_mode")
        assert logic_engine.current_mode == "snoozed" # No change

    def test_cycle_mode(self, logic_engine):
        logic_engine.current_mode = "active"
        logic_engine.cycle_mode()
        assert logic_engine.current_mode == "snoozed"

        logic_engine.cycle_mode()
        assert logic_engine.current_mode == "paused"

        logic_engine.cycle_mode()
        assert logic_engine.current_mode == "active"

    def test_toggle_pause_resume(self, logic_engine):
        logic_engine.current_mode = "active"
        logic_engine.toggle_pause_resume()
        assert logic_engine.current_mode == "paused"
        assert logic_engine.previous_mode_before_pause == "active"

        logic_engine.toggle_pause_resume()
        assert logic_engine.current_mode == "active"

    def test_process_video_data_fallback(self, logic_engine):
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 255

        logic_engine.process_video_data(frame1)
        logic_engine.process_video_data(frame2)

        # Simple diff mean should be roughly 255
        assert logic_engine.video_activity > 250
        assert logic_engine.last_video_frame is not None

    def test_process_audio_data_fallback(self, logic_engine):
        chunk = np.ones(1024)
        logic_engine.process_audio_data(chunk)
        assert logic_engine.audio_level == 1.0
        assert logic_engine.last_audio_chunk is not None

    def test_prepare_lmm_data(self, logic_engine):
        # Must have data
        logic_engine.last_video_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        logic_engine.last_audio_chunk = np.zeros(10)

        data = logic_engine._prepare_lmm_data("test_reason")
        assert data is not None
        assert "video_data" in data
        assert "audio_data" in data
        assert "user_context" in data
        assert data["user_context"]["trigger_reason"] == "test_reason"

    def test_run_lmm_analysis_async_success(self, logic_engine, mock_lmm):
        payload = {"video_data": None, "audio_data": None, "user_context": {}}
        mock_lmm.process_data.return_value = {
            "state_estimation": {"arousal": 10},
            "visual_context": ["phone_usage"]
        }
        mock_lmm.get_intervention_suggestion.return_value = {"id": "test_id"}

        logic_engine._run_lmm_analysis_async(payload, allow_intervention=True)

        logic_engine.state_engine.get_state() # Just to verify no crash
        logic_engine.intervention_engine.start_intervention.assert_called()

    def test_run_lmm_analysis_async_fallback(self, logic_engine, mock_lmm):
        payload = {"video_data": None, "audio_data": None, "user_context": {}}
        # Simulate fallback response
        mock_lmm.process_data.return_value = {
            "_meta": {"is_fallback": True},
            "fallback": True
        }

        logic_engine._run_lmm_analysis_async(payload, allow_intervention=True)

        assert logic_engine.lmm_consecutive_failures == 1

    def test_run_lmm_analysis_async_failure(self, logic_engine, mock_lmm):
        payload = {"video_data": None, "audio_data": None, "user_context": {}}
        mock_lmm.process_data.return_value = None

        logic_engine._run_lmm_analysis_async(payload, allow_intervention=True)

        assert logic_engine.lmm_consecutive_failures == 1

    def test_trigger_lmm_analysis(self, logic_engine):
        # With no data, should return early
        logic_engine._trigger_lmm_analysis("reason")
        assert logic_engine.lmm_thread is None

        # Add data
        logic_engine.last_video_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        logic_engine.last_audio_chunk = np.zeros(10)

        logic_engine._trigger_lmm_analysis("reason")
        assert logic_engine.lmm_thread is not None
        logic_engine.lmm_thread.join()

    def test_update_active_periodic(self, logic_engine):
        logic_engine.current_mode = "active"
        logic_engine.last_lmm_call_time = 0 # Force update
        logic_engine.lmm_call_interval = 0

        # Add data
        logic_engine.last_video_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        logic_engine.last_audio_chunk = np.zeros(10)

        with patch.object(logic_engine, '_trigger_lmm_analysis') as mock_trigger:
            logic_engine.update()
            mock_trigger.assert_called_with(reason="periodic_check", allow_intervention=True)

    def test_visual_context_triggers(self, logic_engine):
        # Doom scroll logic
        assert logic_engine._process_visual_context_triggers(["phone_usage"]) is None
        assert logic_engine._process_visual_context_triggers(["phone_usage"]) is None
        # Assuming threshold is 3
        result = logic_engine._process_visual_context_triggers(["phone_usage"])
        assert result == "doom_scroll_breaker"

    def test_error_recovery(self, logic_engine):
        logic_engine.current_mode = "error"
        logic_engine.last_error_recovery_attempt_time = 0
        logic_engine.error_recovery_interval = 0

        logic_engine.update()

        assert logic_engine.error_recovery_attempts == 1
        assert logic_engine.current_mode == "active" # Default recovery target

    def test_snooze_expiry(self, logic_engine):
        logic_engine.current_mode = "snoozed"
        logic_engine.snooze_end_time = time.time() - 1 # Already expired

        logic_engine.update()

        assert logic_engine.current_mode == "active"

    def test_shutdown(self, logic_engine):
        logic_engine.shutdown()
        # Verify nothing exploded
