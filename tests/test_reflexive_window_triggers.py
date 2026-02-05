import pytest
import time
from unittest.mock import MagicMock, patch
from core.logic_engine import LogicEngine
import config

class TestReflexiveWindowTriggers:

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def mock_window_sensor(self):
        sensor = MagicMock()
        sensor.get_active_window.return_value = "Unknown"
        return sensor

    @pytest.fixture
    def mock_intervention_engine(self):
        return MagicMock()

    @pytest.fixture
    def logic_engine(self, mock_logger, mock_window_sensor, mock_intervention_engine):
        engine = LogicEngine(window_sensor=mock_window_sensor, logger=mock_logger)
        engine.set_intervention_engine(mock_intervention_engine)
        # Ensure we are in active mode
        engine.current_mode = "active"
        return engine

    def test_reflexive_trigger_match(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        # Setup config
        triggers = {"Game": "alert_id"}
        cooldown = 10

        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', triggers), \
             patch.object(config, 'REFLEXIVE_WINDOW_COOLDOWN', cooldown):

            # 1. First match
            mock_window_sensor.get_active_window.return_value = "My Game Window"
            # Force update (bypass interval check by manipulating last_reflexive_check_time)
            logic_engine.last_reflexive_check_time = 0

            logic_engine.update()

            # Assert intervention started
            mock_intervention_engine.start_intervention.assert_called_with({"id": "alert_id"})

            # Reset mock
            mock_intervention_engine.start_intervention.reset_mock()

            # 2. Immediate second match (should be cooldown)
            logic_engine.last_reflexive_check_time = 0 # Force check
            # We also need to make sure time hasn't advanced past cooldown (it hasn't)
            logic_engine.update()

            mock_intervention_engine.start_intervention.assert_not_called()

            # 3. After cooldown
            # Manually expire the cooldown
            logic_engine.last_reflexive_trigger_time["Game"] -= (cooldown + 1)
            logic_engine.last_reflexive_check_time = 0

            logic_engine.update()
            mock_intervention_engine.start_intervention.assert_called_with({"id": "alert_id"})

    def test_no_match(self, logic_engine, mock_window_sensor, mock_intervention_engine):
         with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Game": "alert_id"}):
            mock_window_sensor.get_active_window.return_value = "Work Document"
            logic_engine.last_reflexive_check_time = 0

            logic_engine.update()

            mock_intervention_engine.start_intervention.assert_not_called()

    def test_case_insensitive_match(self, logic_engine, mock_window_sensor, mock_intervention_engine):
         with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"steam": "alert_id"}):
            mock_window_sensor.get_active_window.return_value = "Steam - Library"
            logic_engine.last_reflexive_check_time = 0

            logic_engine.update()

            mock_intervention_engine.start_intervention.assert_called_with({"id": "alert_id"})

    def test_unknown_window_ignored(self, logic_engine, mock_window_sensor, mock_intervention_engine):
         with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"steam": "alert_id"}):
            mock_window_sensor.get_active_window.return_value = "Unknown"
            logic_engine.last_reflexive_check_time = 0

            logic_engine.update()

            mock_intervention_engine.start_intervention.assert_not_called()

    def test_throttling(self, logic_engine, mock_window_sensor, mock_intervention_engine):
        """Verify that window sensor is not polled if interval hasn't passed."""
        # Prevent history snapshot from triggering
        logic_engine.last_history_sample_time = time.time()

        with patch.object(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Game": "alert_id"}):
            mock_window_sensor.get_active_window.return_value = "Game Window"

            # 1. First call (should check)
            logic_engine.last_reflexive_check_time = 0
            logic_engine.update()
            assert mock_window_sensor.get_active_window.call_count == 1

            # 2. Second call immediately (should skip check)
            # logic_engine.last_reflexive_check_time was updated in step 1
            logic_engine.update()
            assert mock_window_sensor.get_active_window.call_count == 1
