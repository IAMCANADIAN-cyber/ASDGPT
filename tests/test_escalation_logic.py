import pytest
import time
from unittest.mock import MagicMock, patch, ANY
from core.intervention_engine import InterventionEngine
import config

class TestEscalationLogic:
    @pytest.fixture
    def engine(self):
        mock_logic = MagicMock()
        mock_logic.get_mode.return_value = "active"
        mock_app = MagicMock()
        mock_app.data_logger = MagicMock()

        # Patch config values that InterventionEngine uses
        # We patch them to ensure consistent state
        with patch('config.MIN_TIME_BETWEEN_INTERVENTIONS', 0), \
             patch('config.REFLEXIVE_WINDOW_COOLDOWN', 0), \
             patch('config.SUPPRESSIONS_FILE', 'user_data/test_suppressions.json'), \
             patch('config.PREFERENCES_FILE', 'user_data/test_preferences.json'):

            engine = InterventionEngine(mock_logic, mock_app)
            # Set escalation window to something manageable
            engine.escalation_window = 10
            # Bypass category cooldowns for testing default behavior
            engine.category_cooldowns = {k: 0 for k in engine.category_cooldowns}

            yield engine

    def test_monotonic_escalation(self, engine):
        """
        Verify that persistent triggers escalate Tier 1 -> Tier 2 -> Tier 3.
        Even if the input request keeps asking for Tier 1.
        """
        intervention_id = "test_intervention"
        category = "default"

        # 1. First trigger: Tier 1
        details_1 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
        with patch.object(engine, '_run_intervention_thread'):
            engine.start_intervention(details_1, category)
            # Manually clear active event since mocked thread won't do it
            engine._intervention_active.clear()

        assert engine.recent_interventions[-1]["tier"] == 1

        # Simulate time passing (less than escalation window)
        time.sleep(0.1)

        # 2. Second trigger: Request Tier 1 -> Should escalate to Tier 2
        details_2 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
        with patch.object(engine, '_run_intervention_thread'):
            engine.start_intervention(details_2, category)
            engine._intervention_active.clear()

        assert engine.recent_interventions[-1]["tier"] == 2

        # Simulate time passing
        time.sleep(0.1)

        # 3. Third trigger: Request Tier 1 -> Should escalate to Tier 3
        details_3 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
        with patch.object(engine, '_run_intervention_thread'):
            engine.start_intervention(details_3, category)
            engine._intervention_active.clear()

        assert engine.recent_interventions[-1]["tier"] == 3

        # Simulate time passing
        time.sleep(0.1)

        # 4. Fourth trigger: Request Tier 1 -> Should Cap at Tier 3
        details_4 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
        with patch.object(engine, '_run_intervention_thread'):
            engine.start_intervention(details_4, category)
            engine._intervention_active.clear()

        assert engine.recent_interventions[-1]["tier"] == 3

    def test_escalation_window_expiry(self, engine):
        """
        Verify that escalation resets if the window expires.
        """
        intervention_id = "test_intervention_expiry"
        category = "default"

        # 1. First trigger: Tier 1
        details_1 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
        with patch.object(engine, '_run_intervention_thread'):
            engine.start_intervention(details_1, category)
            engine._intervention_active.clear()

        assert engine.recent_interventions[-1]["tier"] == 1

        # Simulate time passing > escalation window
        current_time = time.time()
        with patch('time.time', return_value=current_time + engine.escalation_window + 1):
             # 2. Trigger again: Should stay Tier 1 because window expired
            details_2 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
            with patch.object(engine, '_run_intervention_thread'):
                engine.start_intervention(details_2, category)
                engine._intervention_active.clear()

            assert engine.recent_interventions[-1]["tier"] == 1

    def test_escalation_blocked_by_cooldown(self, engine):
        """
        Verify that standard cooldowns block re-triggering if we don't wait long enough (nag interval).
        """
        intervention_id = "test_cooldown_block"
        category = "default"

        # Set a real cooldown
        engine.category_cooldowns[category] = 300 # 5 minutes

        # 1. First trigger: Tier 1
        details_1 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
        with patch.object(engine, '_run_intervention_thread'):
            result = engine.start_intervention(details_1, category)
            engine._intervention_active.clear()

        assert result is True
        assert engine.recent_interventions[-1]["tier"] == 1

        # Simulate 2 seconds passing (inside escalation window, but inside cooldown, and < nag interval)
        engine.last_category_trigger_time[category] = time.time()
        time.sleep(0.1)

        # 2. Trigger again: Should be BLOCKED by category cooldown because delta < nag_interval (15s)
        details_2 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
        with patch.object(engine, '_run_intervention_thread'):
            result = engine.start_intervention(details_2, category)
            # Don't need to clear active here as it shouldn't have started

        assert result is False

    def test_escalation_bypass_success(self, engine):
        """
        Verify that escalation BYPASSES cooldowns if we wait longer than nag interval.
        """
        intervention_id = "test_bypass"
        category = "default"

        # Set a real cooldown (long)
        engine.category_cooldowns[category] = 300

        # Set nag interval (short for test)
        with patch('config.ESCALATION_NAG_INTERVAL', 1.0):

            # 1. First trigger: Tier 1
            details_1 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
            with patch.object(engine, '_run_intervention_thread'):
                res = engine.start_intervention(details_1, category)
                engine._intervention_active.clear()
            assert res is True
            assert engine.recent_interventions[-1]["tier"] == 1

            # 2. Wait 1.5s ( > Nag Interval 1.0s, < Escalation Window 10s)
            current_time = 1000.0

            # Retroactively set first intervention time
            engine.last_category_trigger_time[category] = current_time
            engine.last_intervention_time = current_time
            engine.recent_interventions[-1]["timestamp"] = current_time

            # Now pretend it is current_time + 1.5
            new_time = current_time + 1.5

            with patch('time.time', return_value=new_time):
                details_2 = {"id": intervention_id, "tier": 1, "type": "test", "message": "msg"}
                with patch.object(engine, '_run_intervention_thread'):
                    res = engine.start_intervention(details_2, category)
                    engine._intervention_active.clear()

            # Should SUCCEED (bypass cooldown) and ESCALATE
            assert res is True
            assert engine.recent_interventions[-1]["tier"] == 2
