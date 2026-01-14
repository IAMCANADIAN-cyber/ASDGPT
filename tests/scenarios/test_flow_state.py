import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness

class TestFlowStateScenario(unittest.TestCase):
    def test_flow_state_trajectory(self):
        """
        Tests that the system correctly handles a 'Flow State' trajectory,
        where high activity and potential noise (music) do NOT trigger negative interventions.
        """

        scenario = [
            # Step 1: Entering Flow.
            # User is settling in. Moderate activity.
            {
                "description": "Step 1: Entering Flow (Moderate Activity)",
                "input": {
                    "audio_level": 0.05,
                    "video_activity": 5.0
                },
                "expected_outcome": {
                    "state_change": {"focus": "increase", "arousal": "stable"},
                    "visual_context": ["sitting", "screen_interaction"],
                    "intervention": None
                }
            },
            # Step 2: Intense Flow (Furious Typing).
            # High video activity might look like 'agitation' to a naive system,
            # but LMM should interpret it as High Focus (Flow).
            {
                "description": "Step 2: Intense Flow (High Video Activity)",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 25.0 # High activity!
                },
                "expected_outcome": {
                    "state_change": {"focus": "increase"}, # Focus peaks
                    "expected_state": {"focus": 60}, # Target adjusted for smoothing (one step won't reach 80)
                    "visual_context": ["typing_fast", "focused"],
                    "intervention": None # crucially, NO intervention
                }
            },
            # Step 3: Flow with Background Music.
            # High Audio Level (Music), but NOT speech.
            # LogicEngine should filter this out or LMM should ignore it.
            {
                "description": "Step 3: Flow with Music (High Audio, Non-Speech)",
                "input": {
                    "audio_level": 0.7, # Loud!
                    "video_activity": 10.0
                },
                "input_analysis": {
                    "audio": {"is_speech": False, "rms": 0.7} # Explicitly NOT speech
                },
                "expected_outcome": {
                    "state_change": {"focus": "stable"},
                    "intervention": None
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

        # Step 1: Success
        self.assertTrue(results['step_results'][0]['success'], "Step 1 (Entering Flow) failed")

        # Step 2: Success
        self.assertTrue(results['step_results'][1]['success'], "Step 2 (Intense Flow) failed - Interrupted?")

        # Step 3: Success
        self.assertTrue(results['step_results'][2]['success'], "Step 3 (Music) failed - False Positive Trigger?")

if __name__ == '__main__':
    unittest.main()
