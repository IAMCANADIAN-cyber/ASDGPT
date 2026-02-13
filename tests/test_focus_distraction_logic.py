import pytest
from unittest.mock import MagicMock, patch
import time
import sys
import config
import numpy as np

from core.logic_engine import LogicEngine

class TestFocusDistractionLogic:
    @pytest.fixture
    def mock_window_sensor(self):
        return MagicMock()

    @pytest.fixture
    def mock_intervention_engine(self):
        return MagicMock()

    @pytest.fixture
    def logic_engine(self, mock_window_sensor, mock_intervention_engine):
        # Patch config values
        with patch.object(config, 'DISTRACTION_APPS', ["MyDistractionApp"]), \
             patch.object(config, 'FOCUS_APPS', ["MyFocusApp"]), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 300):

            engine = LogicEngine(window_sensor=mock_window_sensor)
            engine.set_intervention_engine(mock_intervention_engine)
            engine.current_mode = "active"
            yield engine

    def test_distraction_app_trigger(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        # Setup
        mock_window_sensor.get_active_window.return_value = "MyDistractionApp - Home"

        # Act
        logic_engine.update()

        # Assert
        mock_intervention_engine.start_intervention.assert_called_once()
        args, _ = mock_intervention_engine.start_intervention.call_args
        assert args[0]['id'] == "distraction_alert"

    def test_focus_app_context(self, logic_engine, mock_window_sensor):
        # Setup
        mock_window_sensor.get_active_window.return_value = "MyFocusApp - Project"

        # Act
        # We need to call _prepare_lmm_data directly or trigger it via update loop
        # Direct call is easier to verify return payload

        # Need to ensure sensors return something so it doesn't return None
        # LogicEngine checks for last_video_frame and last_audio_chunk
        logic_engine.last_video_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        logic_engine.last_audio_chunk = np.zeros(1024, dtype=np.float32)

        payload = logic_engine._prepare_lmm_data()

        # Assert
        assert payload is not None
        user_context = payload['user_context']
        system_alerts = user_context.get('system_alerts', [])

        found_focus = False
        for alert in system_alerts:
            if "Focus App Active: MyFocusApp" in alert:
                found_focus = True
                break

        assert found_focus, f"Focus app alert not found in system_alerts: {system_alerts}"

    def test_no_trigger_if_not_listed(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        # Setup
        mock_window_sensor.get_active_window.return_value = "SomeRandomApp"

        # Act
        logic_engine.update()

        # Assert
        mock_intervention_engine.start_intervention.assert_not_called()
