import unittest
from unittest.mock import MagicMock
from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine

class TestGamingMode(unittest.TestCase):
    def test_gaming_mode_suppressions(self):
        mock_logic = MagicMock()
        mock_logic.get_mode.return_value = "gaming"

        engine = InterventionEngine(logic_engine=mock_logic)

        # Should reject generic
        result = engine.start_intervention({"type": "distraction_alert", "message": "test"})
        self.assertFalse(result)

        # Should allow critical
        result = engine.start_intervention({"type": "posture_water_reset", "message": "test"})
        self.assertTrue(result)
