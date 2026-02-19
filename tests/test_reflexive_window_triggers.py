import pytest
from unittest.mock import MagicMock, patch
import time
import sys
import config

from core.logic_engine import LogicEngine

class TestReflexiveWindowTriggers:
    @pytest.fixture
    def mock_window_sensor(self):
        return MagicMock()

    @pytest.fixture
    def mock_intervention_engine(self):
        return MagicMock()

    @pytest.fixture
    def logic_engine(self, mock_window_sensor, mock_intervention_engine):
        # Patch config values
        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Steam": "distraction_alert"}), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 300):

            engine = LogicEngine(window_sensor=mock_window_sensor)
            engine.set_intervention_engine(mock_intervention_engine)
            engine.current_mode = "active"
            return engine

    def test_reflexive_trigger_activates(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        # Setup
        mock_window_sensor.get_active_window.return_value = "Steam - Library"

        # Act
        logic_engine.update()

        # Assert
        mock_intervention_engine.start_intervention.assert_called_once()
        args, _ = mock_intervention_engine.start_intervention.call_args
        assert args[0]['id'] == "distraction_alert"
        assert args[0]['tier'] == 2

    def test_reflexive_trigger_delegates_cooldown(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        # Setup
        mock_window_sensor.get_active_window.return_value = "Steam - Library"

        # Fire once
        logic_engine.update()
        mock_intervention_engine.start_intervention.assert_called_once()
        mock_intervention_engine.start_intervention.reset_mock()

        # Act - Fire immediately again
        logic_engine.update()

        # Assert - LogicEngine should attempt to trigger again (delegating cooldown)
        mock_intervention_engine.start_intervention.assert_called_once()
        args, kwargs = mock_intervention_engine.start_intervention.call_args
        assert kwargs.get("category") == "reflexive_window"

    def test_no_trigger_on_mismatch(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        # Setup
        mock_window_sensor.get_active_window.return_value = "Visual Studio Code"

        # Act
        logic_engine.update()

        # Assert
        mock_intervention_engine.start_intervention.assert_not_called()

    def test_no_trigger_in_dnd_mode(self, logic_engine, mock_window_sensor, mock_intervention_engine):
         # Setup
        mock_window_sensor.get_active_window.return_value = "Steam - Library"
        logic_engine.current_mode = "dnd"

        # Act
        logic_engine.update()

        # Assert
        mock_intervention_engine.start_intervention.assert_not_called()

    def test_trigger_partial_match_case_insensitive(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        # Setup
        mock_window_sensor.get_active_window.return_value = "Playing sTeAm game"

        # Act
        logic_engine.update()

        # Assert
        mock_intervention_engine.start_intervention.assert_called_once()
