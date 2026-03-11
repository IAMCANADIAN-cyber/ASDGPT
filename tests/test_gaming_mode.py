import unittest
from unittest.mock import MagicMock
import sys
import os

from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine
from core.data_logger import DataLogger
import config

class TestGamingMode(unittest.TestCase):
    def setUp(self):
        self.logger = DataLogger()
        self.logic_engine = LogicEngine(logger=self.logger)
        self.logic_engine.get_mode = MagicMock(return_value="gaming")

        self.intervention_engine = InterventionEngine(
            logic_engine=self.logic_engine
        )
        self.intervention_engine._play_sound = MagicMock()
        self.intervention_engine._wait = MagicMock()
        self.intervention_engine.voice_interface = MagicMock()

    def test_gaming_mode_allows_posture_reset(self):
        payload = {"type": "posture_water_reset", "message": "Posture check"}
        result = self.intervention_engine.start_intervention(payload)
        self.assertTrue(result, "posture_water_reset should be allowed in gaming mode")

    def test_gaming_mode_suppresses_distraction(self):
        payload = {"type": "distraction_alert", "message": "Distraction"}
        result = self.intervention_engine.start_intervention(payload)
        self.assertFalse(result, "distraction_alert should be suppressed in gaming mode")

if __name__ == '__main__':
    unittest.main()
