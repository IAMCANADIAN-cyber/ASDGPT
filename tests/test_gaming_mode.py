import unittest
from unittest.mock import MagicMock
import time
from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine

class TestGamingMode(unittest.TestCase):
    def setUp(self):
        self.logic_engine = LogicEngine(
            audio_sensor=MagicMock(),
            video_sensor=MagicMock(),
            window_sensor=MagicMock(),
            lmm_interface=MagicMock()
        )
        self.intervention_engine = InterventionEngine(MagicMock())
        self.intervention_engine.logic_engine = self.logic_engine

    def tearDown(self):
        self.logic_engine.shutdown()

    def test_gaming_mode_suppression(self):
        self.logic_engine.set_mode("gaming")
        self.assertEqual(self.logic_engine.get_mode(), "gaming")

        # Test non-critical intervention
        result = self.intervention_engine.start_intervention({"id": "distraction_alert"})
        self.assertFalse(result)

        # Test critical intervention
        result = self.intervention_engine.start_intervention({"id": "posture_water_reset"})
        self.assertTrue(result)

    def test_high_video_activity_suppression(self):
        self.logic_engine.set_mode("gaming")
        self.logic_engine.video_activity = 1000.0  # High activity
        self.logic_engine.face_metrics = {"face_detected": True, "face_count": 1}
        self.logic_engine.update()
        self.assertEqual(self.logic_engine.get_mode(), "gaming")

if __name__ == '__main__':
    unittest.main()
