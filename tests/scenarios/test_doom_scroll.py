import unittest
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
import config

class TestDoomScrollScenario(unittest.TestCase):
    def test_doom_scroll_trigger(self):
        """
        Tests that the system correctly identifies a 'doom scroll' pattern
        after persistent visual context cues and triggers the 'doom_scroll_breaker' intervention.
        """

        # Define the scenario
        # We need consecutive detections to trigger the persistence alert.
        # DOOM_SCROLL_THRESHOLD is default 3.

        scenario = [
            # Step 1: User holding phone.
            # LogicEngine should NOT trigger intervention yet (count = 1).
            {
                "description": "Step 1: Phone usage detected (Count 1)",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 5.0 # Low activity
                },
                "expected_outcome": {
                    "visual_context": ["phone_usage", "looking_down"],
                    "state_change": {"focus": "decrease"},
                    "intervention": None
                }
            },
            # Step 2: Still holding phone.
            # LogicEngine should NOT trigger intervention yet (count = 2).
            {
                "description": "Step 2: Phone usage detected (Count 2)",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 5.0
                },
                "expected_outcome": {
                    "visual_context": ["phone_usage"],
                    "state_change": {"focus": "decrease"},
                    "intervention": None
                }
            },
            # Step 3: Still holding phone.
            # LogicEngine SHOULD trigger intervention (count = 3 >= threshold).
            {
                "description": "Step 3: Phone usage detected (Count 3) -> Trigger",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 5.0
                },
                "expected_outcome": {
                    "visual_context": ["phone_usage"],
                    "state_change": {"focus": "decrease"},
                    "intervention": "doom_scroll_breaker"
                }
            }
        ]

        # Initialize Harness
        harness = ReplayHarness()

        # Run Scenario
        results = harness.run_scenario(scenario)
        harness.print_report(results)

        # Assertions
        self.assertEqual(results['total_steps'], 3)

        # Check specific steps
        # Step 1: Success
        self.assertTrue(results['step_results'][0]['success'], "Step 1 failed")
        # Step 2: Success
        self.assertTrue(results['step_results'][1]['success'], "Step 2 failed")
        # Step 3: Success
        self.assertTrue(results['step_results'][2]['success'], "Step 3 failed")

if __name__ == '__main__':
    unittest.main()
