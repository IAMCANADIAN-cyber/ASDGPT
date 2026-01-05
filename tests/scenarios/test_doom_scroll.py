import unittest
import numpy as np
import sys
import os

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.replay_harness import ReplayHarness

class TestDoomScrollScenario(unittest.TestCase):
    def test_doom_scroll_trigger(self):
        """
        Scenario: User is detected using phone for 3 consecutive updates (persistence).
        Expectation: 'doom_scroll_breaker' intervention is triggered automatically.
        """
        harness = ReplayHarness()

        # Override threshold to be sure (default is 3)
        harness.logic_engine.doom_scroll_trigger_threshold = 3

        # 1. First Update: LMM sees phone
        harness.add_lmm_response({
            "state_estimation": {"focus": 20},
            "visual_context": ["phone_usage"],
            "suggestion": None
        })
        # Trigger via periodic check or manual trigger logic
        # We simulate video activity to trigger LMM
        frame1 = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        harness.run_step(video_frame=frame1)

        # 2. Second Update: LMM sees phone
        harness.add_lmm_response({
            "state_estimation": {"focus": 15},
            "visual_context": ["phone_usage"],
            "suggestion": None
        })
        frame2 = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        harness.run_step(video_frame=frame2)

        # 3. Third Update: LMM sees phone -> TRIGGER
        harness.add_lmm_response({
            "state_estimation": {"focus": 10},
            "visual_context": ["phone_usage"],
            "suggestion": None
        })
        frame3 = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        harness.run_step(video_frame=frame3)

        # Verify
        results = harness.get_results()
        interventions = results["interventions"]

        self.assertTrue(len(interventions) > 0, "No intervention triggered")
        self.assertEqual(interventions[0]["id"], "doom_scroll_breaker", "Wrong intervention triggered")

if __name__ == '__main__':
    unittest.main()
