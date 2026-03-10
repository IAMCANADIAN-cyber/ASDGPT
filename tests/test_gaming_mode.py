import unittest
from unittest.mock import MagicMock, patch
import time

from core.logic_engine import LogicEngine
from core.intervention_engine import InterventionEngine
import config

class TestGamingMode(unittest.TestCase):

    def setUp(self):
        self.logic_engine = LogicEngine()
        self.logic_engine.lmm_interface = MagicMock()
        self.logic_engine.intervention_engine = MagicMock()

        # Avoid thread starting in init
        self.app_mock = MagicMock()
        self.app_mock.data_logger = MagicMock()
        self.intervention_engine = InterventionEngine(self.logic_engine, self.app_mock)

        # Mocks to prevent thread blocking / actual sounds
        patcher_play = patch.object(self.intervention_engine, '_play_sound')
        self.mock_play = patcher_play.start()
        self.addCleanup(patcher_play.stop)

        patcher_speak = patch.object(self.intervention_engine, '_speak')
        self.mock_speak = patcher_speak.start()
        self.addCleanup(patcher_speak.stop)

    def test_logic_engine_suppresses_video_activity_in_gaming_mode(self):
        self.logic_engine.set_mode("gaming")

        # Trigger high video activity
        self.logic_engine.video_activity = config.VIDEO_ACTIVITY_THRESHOLD_HIGH + 100
        self.logic_engine.face_metrics["face_detected"] = True

        self.logic_engine.update()

        with patch('time.time', return_value=self.logic_engine.last_lmm_call_time + 1):
            self.logic_engine.update()

        self.logic_engine.lmm_interface.process_data.assert_not_called()

    def test_intervention_engine_gaming_mode_filters(self):
        self.logic_engine.get_mode = MagicMock(return_value="gaming")

        # Reset cooldowns
        self.intervention_engine.last_intervention_time = 0
        self.intervention_engine.last_category_trigger_time = {}

        # 1. Non-critical intervention should be blocked
        result = self.intervention_engine.start_intervention({"type": "take_break", "message": "Break"})
        self.assertFalse(result)

        # 2. Critical/System intervention should be allowed
        result = self.intervention_engine.start_intervention({"type": "error_notification", "message": "Error"}, category="system")
        self.assertTrue(result)
        self.intervention_engine.stop_intervention() # clear state

        # Ensure thread finishes
        if self.intervention_engine.intervention_thread:
            self.intervention_engine.intervention_thread.join(timeout=1.0)

        # 3. Posture water reset should be allowed
        # It's not a bypass_global category by default, so it might fail global cooldown if not handled
        # But we reset the cooldown earlier. Wait, start_intervention sets last_intervention_time!
        # So we must reset it again before test 3
        self.intervention_engine.last_intervention_time = 0

        result = self.intervention_engine.start_intervention({"id": "posture_water_reset"})
        self.assertTrue(result)
        self.intervention_engine.stop_intervention()

if __name__ == '__main__':
    unittest.main()
