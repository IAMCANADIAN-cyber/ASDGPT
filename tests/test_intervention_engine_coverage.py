import pytest
from unittest.mock import MagicMock, patch, ANY, call
import time
import os
import json
import threading
import sys

# Mock config before imports
sys.modules['config'] = MagicMock()
sys.modules['config'].FEEDBACK_WINDOW_SECONDS = 5
sys.modules['config'].MIN_TIME_BETWEEN_INTERVENTIONS = 0.1
sys.modules['config'].FEEDBACK_SUPPRESSION_MINUTES = 60
sys.modules['config'].SUPPRESSIONS_FILE = "suppressions.json"
sys.modules['config'].PREFERENCES_FILE = "preferences.json"
sys.modules['config'].SNOOZE_DURATION = 60

from core.intervention_engine import InterventionEngine

class TestInterventionEngineCoverage:
    @pytest.fixture
    def mock_logic_engine(self):
        le = MagicMock()
        le.get_mode.return_value = "active"
        le.last_video_frame = None # Default
        return le

    @pytest.fixture
    def mock_app(self):
        app = MagicMock()
        app.data_logger = MagicMock()
        app.tray_icon = MagicMock()
        return app

    @pytest.fixture
    def engine(self, mock_logic_engine, mock_app):
        # Patch load/save to avoid file IO during init
        with patch.object(InterventionEngine, '_load_suppressions'), \
             patch.object(InterventionEngine, '_load_preferences'):
            ie = InterventionEngine(mock_logic_engine, mock_app)
            return ie

    def test_init(self, engine):
        assert engine.library is not None
        assert engine._intervention_active is not None

    def test_load_save_suppressions(self, engine):
        # We need to test the actual file IO logic, but safely
        # Using mocks for open/json
        with patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('json.load') as mock_json_load, \
             patch('os.path.exists', return_value=True):

            mock_json_load.return_value = {"test_type": time.time() + 100}
            engine._load_suppressions()
            assert "test_type" in engine.suppressed_interventions

        # Verify save works
        with patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('json.dump') as mock_json_dump, \
             patch('os.makedirs'):

            engine._save_suppressions()
            mock_json_dump.assert_called_once()


    def test_load_save_preferences(self, engine):
        with patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('json.load') as mock_json_load, \
             patch('os.path.exists', return_value=True):

            mock_json_load.return_value = {"test_type": {"count": 1}}
            engine._load_preferences()
            assert "test_type" in engine.preferred_interventions

        with patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('json.dump') as mock_json_dump, \
             patch('os.makedirs'):

            engine._save_preferences()
            mock_json_dump.assert_called_once()

    def test_speak_platform(self, engine):
        # Ensure intervention is active so blocking speak proceeds
        engine._intervention_active.set()

        with patch('platform.system', return_value="Linux"), \
             patch('subprocess.Popen') as mock_popen:

            engine._speak("Test", blocking=True)
            mock_popen.assert_called()

    def test_play_sound_missing_file(self, engine):
        with patch('os.path.exists', return_value=False):
            engine._play_sound("missing.wav")
            engine.app.data_logger.log_warning.assert_called()

    def test_show_visual_prompt(self, engine):
        # Mock Image
        with patch('core.intervention_engine.Image') as MockImage:
            with patch('os.path.exists', return_value=True):
                engine._show_visual_prompt("test.jpg")
                MockImage.open.assert_called_with("test.jpg")

    def test_capture_image(self, engine):
        # Mock cv2
        with patch('core.intervention_engine.cv2') as mock_cv2:
            engine.logic_engine.last_video_frame = "frame_data"
            with patch('os.path.exists', return_value=False), \
                 patch('os.makedirs'):
                engine._capture_image("details")
                mock_cv2.imwrite.assert_called()

    def test_record_video(self, engine):
         with patch('core.intervention_engine.cv2') as mock_cv2:
            mock_frame = MagicMock()
            mock_frame.shape = (100, 100, 3)
            engine.logic_engine.last_video_frame = mock_frame

            with patch('os.path.exists', return_value=False), \
                 patch('os.makedirs'), \
                 patch('time.sleep'): # Speed up loop
                # Ensure intervention is active
                engine._intervention_active.set()
                engine._record_video("details")
                mock_cv2.VideoWriter.assert_called()

    def test_wait(self, engine):
        start = time.time()
        engine._intervention_active.set()
        # Mock sleep to return immediately or run fast
        with patch('time.sleep'):
             # We can't easily mock time.time() to increment in a loop without side effects
             # So we just test that it respects the flag
             engine._intervention_active.clear() # Should exit loop immediately
             engine._wait(10)
        # Should be fast
        assert time.time() - start < 1

    def test_run_sequence(self, engine):
        sequence = [
            {"action": "speak", "content": "hi"},
            {"action": "wait", "duration": 0},
            {"action": "unknown"}
        ]
        engine._intervention_active.set()

        with patch.object(engine, '_speak') as mock_speak, \
             patch.object(engine, '_wait') as mock_wait:

            engine._run_sequence(sequence, engine.app.data_logger)
            mock_speak.assert_called()
            mock_wait.assert_called()
            engine.app.data_logger.log_warning.assert_called_with("Unknown action in sequence: unknown")

    def test_suppress_intervention(self, engine):
        with patch.object(engine, '_save_suppressions'):
            engine.suppress_intervention("test", 10)
            assert "test" in engine.suppressed_interventions
            assert engine.suppressed_interventions["test"] > time.time()

    def test_get_suppressed_intervention_types(self, engine):
        engine.suppressed_interventions = {
            "valid": time.time() + 100,
            "expired": time.time() - 100
        }
        with patch.object(engine, '_save_suppressions'):
            active = engine.get_suppressed_intervention_types()
            assert "valid" in active
            assert "expired" not in active
            assert "expired" not in engine.suppressed_interventions

    def test_get_preferred_intervention_types(self, engine):
        engine.preferred_interventions = {
            "a": {"count": 5},
            "b": {"count": 10}
        }
        prefs = engine.get_preferred_intervention_types()
        assert prefs == ["b", "a"]

    def test_start_intervention_success(self, engine):
        details = {"type": "test", "message": "msg"}

        with patch('threading.Thread'):
             result = engine.start_intervention(details)
             assert result is True
             assert engine._intervention_active.is_set()

    def test_start_intervention_suppressed(self, engine):
        details = {"type": "test", "message": "msg"}
        engine.suppressed_interventions = {"test": time.time() + 100}

        result = engine.start_intervention(details)
        assert result is False

    def test_start_intervention_mode_check(self, engine):
        details = {"type": "test", "message": "msg"}
        engine.logic_engine.get_mode.return_value = "paused"

        result = engine.start_intervention(details)
        assert result is False

    def test_start_intervention_rate_limit(self, engine):
        details = {"type": "test", "message": "msg"}
        engine.last_intervention_time = time.time()

        result = engine.start_intervention(details)
        assert result is False

    def test_start_intervention_priority(self, engine):
        # Set active intervention
        engine._intervention_active.set()
        engine._current_intervention_details = {"tier": 1}

        details_high = {"type": "high", "message": "urgent", "tier": 2}

        with patch('threading.Thread'), patch.object(engine, 'stop_intervention') as mock_stop:
            result = engine.start_intervention(details_high)
            assert result is True
            mock_stop.assert_called()

        # Low priority should fail
        engine._intervention_active.set()
        engine._current_intervention_details = {"tier": 2}
        details_low = {"type": "low", "message": "meh", "tier": 1}

        result = engine.start_intervention(details_low)
        assert result is False

    def test_stop_intervention(self, engine):
        engine._intervention_active.set()
        engine._current_subprocess = MagicMock()

        engine.stop_intervention()

        assert not engine._intervention_active.is_set()
        engine._current_subprocess.terminate.assert_called()

    def test_notify_mode_change(self, engine):
        with patch.object(engine, '_speak') as mock_speak:
            engine.notify_mode_change("paused")
            mock_speak.assert_called_with("Co-regulator paused.", blocking=False)

    def test_register_feedback_valid(self, engine):
        engine.last_feedback_eligible_intervention = {
            "message": "msg",
            "type": "type",
            "timestamp": time.time()
        }

        with patch.object(engine, '_save_preferences'):
            engine.register_feedback("helpful")
            assert "type" in engine.preferred_interventions
            assert engine.preferred_interventions["type"]["count"] == 1

    def test_register_feedback_unhelpful(self, engine):
        engine.last_feedback_eligible_intervention = {
            "message": "msg",
            "type": "type",
            "timestamp": time.time()
        }

        with patch.object(engine, 'suppress_intervention') as mock_suppress:
            engine.register_feedback("unhelpful")
            mock_suppress.assert_called()

    def test_register_feedback_expired(self, engine):
        engine.last_feedback_eligible_intervention = {
            "message": "msg",
            "type": "type",
            "timestamp": time.time() - 100
        }

        engine.register_feedback("helpful")
        # Should do nothing (check log calls if needed, or lack of preference update)
        assert "type" not in engine.preferred_interventions

    def test_shutdown(self, engine):
        engine.shutdown()
        assert not engine._intervention_active.is_set()
