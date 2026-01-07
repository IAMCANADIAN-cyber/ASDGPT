import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
import config

class TestStatePolicyIntegration(unittest.TestCase):
    def test_overload_smoothing_and_convergence(self):
        """
        Tests the full integration loop:
        1. Injecting high 'overload' sensor data (simulated via LMM output).
        2. Verifying StateEngine smooths the transition (doesn't jump instantly).
        3. Verifying StateEngine eventually converges to the target state.
        """

        # We simulate 5 steps of high overload input (90).
        # Baseline is 0.
        # History size is 5.
        # Step 1: Input 90. Hist=[0,0,0,0,90]. Avg=18.
        # Step 2: Input 90. Hist=[0,0,0,90,90]. Avg=36.
        # Step 3: Input 90. Hist=[0,0,90,90,90]. Avg=54.
        # Step 4: Input 90. Hist=[0,90,90,90,90]. Avg=72.
        # Step 5: Input 90. Hist=[90,90,90,90,90]. Avg=90.

        scenario = [
            {
                "description": "Step 1: Initial Spike",
                "input": {"audio_level": 0.5, "video_activity": 10},
                "expected_outcome": {
                    "state_estimation": {"overload": 90},
                    "expected_state": {"overload": 18}, # 90/5
                    "intervention": None
                }
            },
            {
                "description": "Step 2: Sustained High",
                "input": {"audio_level": 0.5, "video_activity": 10},
                "expected_outcome": {
                    "state_estimation": {"overload": 90},
                    "expected_state": {"overload": 36}, # 180/5
                    "intervention": None
                }
            },
            {
                "description": "Step 3: Sustained High",
                "input": {"audio_level": 0.5, "video_activity": 10},
                "expected_outcome": {
                    "state_estimation": {"overload": 90},
                    "expected_state": {"overload": 54}, # 270/5
                    "intervention": None
                }
            },
            {
                "description": "Step 4: Sustained High",
                "input": {"audio_level": 0.5, "video_activity": 10},
                "expected_outcome": {
                    "state_estimation": {"overload": 90},
                    "expected_state": {"overload": 72}, # 360/5
                    "intervention": None
                }
            },
            {
                "description": "Step 5: Convergence",
                "input": {"audio_level": 0.5, "video_activity": 10},
                "expected_outcome": {
                    "state_estimation": {"overload": 90},
                    "expected_state": {"overload": 90}, # 450/5
                    "intervention": None
                }
            }
        ]

        harness = ReplayHarness()

        # Override baseline to 0 for overload for clean math
        # We need to hack the state engine history because it initializes based on config.
        # ReplayHarness initializes LogicEngine -> StateEngine.
        # We can reset it.
        from collections import deque
        for dim in harness.logic_engine.state_engine.history:
            harness.logic_engine.state_engine.history[dim] = deque([0]*5, maxlen=5)
            harness.logic_engine.state_engine.state[dim] = 0

        results = harness.run_scenario(scenario)
        harness.print_report(results)

        self.assertEqual(results['total_steps'], 5)
        for i, step_res in enumerate(results['step_results']):
            self.assertTrue(step_res['success'], f"Step {i+1} failed: {step_res}")

    def test_state_rejection_of_invalid_input(self):
        """
        Tests that invalid state values (out of bounds) are handled gracefully (ignored or clamped).
        """
        scenario = [
             {
                "description": "Step 1: Invalid High Value",
                "input": {"audio_level": 0.5, "video_activity": 10},
                "expected_outcome": {
                    "state_estimation": {"overload": 200}, # Should be clamped to 100
                    # If clamped to 100: Hist=[0,0,0,0,100] -> Avg=20
                    "expected_state": {"overload": 20},
                    "intervention": None
                }
            }
        ]

        harness = ReplayHarness()
        # Reset history
        from collections import deque
        for dim in harness.logic_engine.state_engine.history:
            harness.logic_engine.state_engine.history[dim] = deque([0]*5, maxlen=5)
            harness.logic_engine.state_engine.state[dim] = 0

        results = harness.run_scenario(scenario)
        harness.print_report(results)

        self.assertTrue(results['step_results'][0]['success'])

if __name__ == '__main__':
    unittest.main()
