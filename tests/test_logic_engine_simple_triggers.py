import pytest
from unittest.mock import MagicMock, patch
import config
from core.logic_engine import LogicEngine

class TestLogicEngineSimpleTriggers:
    @pytest.fixture
    def mock_window_sensor(self):
        return MagicMock()

    @pytest.fixture
    def mock_intervention_engine(self):
        return MagicMock()

    @pytest.fixture
    def logic_engine(self, mock_window_sensor, mock_intervention_engine):
        # Patch config values for testing
        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {}), \
             patch.object(config, 'DISTRACTION_APPS', ["TestDistraction", "Game"]), \
             patch.object(config, 'FOCUS_APPS', ["TestFocus"]), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 0):

            engine = LogicEngine(window_sensor=mock_window_sensor)
            engine.set_intervention_engine(mock_intervention_engine)
            engine.current_mode = "active"
            yield engine

    def test_distraction_app_triggers_alert(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        # Setup
        mock_window_sensor.get_active_window.return_value = "TestDistraction"

        # Act
        logic_engine.update()

        # Assert
        mock_intervention_engine.start_intervention.assert_called_once()
        args, _ = mock_intervention_engine.start_intervention.call_args
        assert args[0]['id'] == "distraction_alert"

    def test_focus_app_does_not_trigger_alert(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        # Setup
        mock_window_sensor.get_active_window.return_value = "TestFocus - Document"

        # Act
        logic_engine.update()

        # Assert
        mock_intervention_engine.start_intervention.assert_not_called()

    def test_focus_app_suppresses_distraction(self, mock_window_sensor, mock_intervention_engine):
        # Ensure that if a window matches both Focus and Distraction, it is considered SAFE.
        # E.g., "VS Code" vs "Code" (if "Code" was a distraction keyword)
        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {}), \
             patch.object(config, 'DISTRACTION_APPS', ["Code"]), \
             patch.object(config, 'FOCUS_APPS', ["VS Code"]), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 0):

            engine = LogicEngine(window_sensor=mock_window_sensor)
            engine.set_intervention_engine(mock_intervention_engine)
            engine.current_mode = "active"

            mock_window_sensor.get_active_window.return_value = "VS Code - Project"

            engine.update()

            # Should NOT trigger "distraction_alert" because "VS Code" is in Focus Apps
            mock_intervention_engine.start_intervention.assert_not_called()

    def test_reflexive_trigger_overrides_distraction(self, mock_window_sensor, mock_intervention_engine):
        # This test ensures that if a window matches BOTH a custom trigger AND a distraction list,
        # the custom trigger wins.
        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Game": "custom_game_alert"}), \
             patch.object(config, 'DISTRACTION_APPS', ["Game"]), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', 0):

            engine = LogicEngine(window_sensor=mock_window_sensor)
            engine.set_intervention_engine(mock_intervention_engine)
            engine.current_mode = "active"

            mock_window_sensor.get_active_window.return_value = "Playing Game"

            engine.update()

            mock_intervention_engine.start_intervention.assert_called_once()
            args, _ = mock_intervention_engine.start_intervention.call_args
            assert args[0]['id'] == "custom_game_alert"
            # Should NOT be "distraction_alert"
