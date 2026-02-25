import unittest
from unittest.mock import MagicMock, patch
import time
from collections import deque
import shutil
import tempfile
import os

from core.intervention_engine import InterventionEngine
import config

class TestEscalationPolicy(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        # Patch config constants
        self.config_patcher = patch.multiple(config,
            ESCALATION_NAG_INTERVAL=15,
            MAX_INTERVENTION_TIER=3,
            MIN_TIME_BETWEEN_INTERVENTIONS=300,
            USER_DATA_DIR=self.test_dir
        )
        self.config_patcher.start()

        self.mock_logic = MagicMock()
        self.mock_logic.get_mode.return_value = "active"
        self.mock_app = MagicMock()

        # Mock dependencies
        self.patches = [
            patch('core.intervention_engine.sd', MagicMock()),
            patch('core.intervention_engine.wavfile', MagicMock()),
            patch('core.intervention_engine.Image', MagicMock()),
            patch('threading.Thread') # Mock threads to prevent actual execution
        ]
        for p in self.patches:
            p.start()

        self.engine = InterventionEngine(self.mock_logic, self.mock_app)
        # Ensure engine uses our patched values
        self.engine.escalation_nag_interval = 15
        self.engine.max_intervention_tier = 3
        self.engine.escalation_window = 60

        # Mock Library to accept "trigger_A"
        self.engine.library = MagicMock()
        def get_intervention_mock(iid):
            if iid in ["trigger_A", "trigger_B"]:
                return {"id": iid, "tier": 1, "description": "Mock"}
            return None
        self.engine.library.get_intervention_by_id.side_effect = get_intervention_mock

    def tearDown(self):
        self.config_patcher.stop()
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.test_dir)

    def test_standard_cooldown(self):
        """Test that distinct interventions respect standard cooldown."""
        # 1. Trigger A
        self.engine.start_intervention({"id": "trigger_A", "tier": 1}, category="default")

        # 2. Trigger B (different ID) immediately
        # Should be blocked by global cooldown (MIN_TIME_BETWEEN_INTERVENTIONS=300)
        success = self.engine.start_intervention({"id": "trigger_B", "tier": 1}, category="default")
        self.assertFalse(success, "Trigger B should be blocked by global cooldown")

    def test_spam_protection(self):
        """Test that same intervention < Nag Interval is suppressed."""
        base_time = 1000.0
        self.engine.last_intervention_time = base_time
        self.engine.recent_interventions.clear()
        self.engine.recent_interventions.append({
            "timestamp": base_time,
            "id": "trigger_A",
            "tier": 1
        })

        with patch('time.time', return_value=base_time + 5):
            success = self.engine.start_intervention({"id": "trigger_A", "tier": 1}, category="default")
            self.assertFalse(success, "Trigger A (repeat) should be blocked by Nag Interval")

    def test_escalation_bypass(self):
        """Test that same intervention > Nag Interval bypasses cooldown and escalates."""
        base_time = 1000.0

        # Set initial state
        self.engine.last_intervention_time = base_time
        self.engine.recent_interventions.clear()
        self.engine.recent_interventions.append({
            "timestamp": base_time,
            "id": "trigger_A",
            "tier": 1
        })

        # Trigger A again at t=1020
        with patch('time.time', return_value=base_time + 20):
            success = self.engine.start_intervention({"id": "trigger_A", "tier": 1}, category="default")

            self.assertTrue(success, "Trigger A should bypass cooldown due to escalation logic")

            # Check Tier: min(3, max(1, 1+1)) = 2
            self.assertEqual(self.engine._current_intervention_details["tier"], 2, "Should escalate to Tier 2")

    def test_max_tier_cap(self):
        """Test that escalation respects MAX_INTERVENTION_TIER."""
        base_time = 1000.0

        # Set state: Last was Tier 3 at t=1000
        self.engine.last_intervention_time = base_time
        self.engine.recent_interventions.clear()
        self.engine.recent_interventions.append({
            "timestamp": base_time,
            "id": "trigger_A",
            "tier": 3
        })

        # Trigger A again at t=1020
        with patch('time.time', return_value=base_time + 20):
             success = self.engine.start_intervention({"id": "trigger_A", "tier": 1}, category="default")
             self.assertTrue(success)
             # Check Tier: min(3, max(1, 3+1)) = 3
             self.assertEqual(self.engine._current_intervention_details["tier"], 3, "Should remain capped at Tier 3")

if __name__ == '__main__':
    unittest.main()
