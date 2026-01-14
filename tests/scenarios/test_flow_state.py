import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
import config

class TestFlowStateScenario(unittest.TestCase):
    def test_flow_state_trigger(self):
        """
        Tests that the system correctly identifies a 'Flow State' (High Focus, High Activity, No Speech)
        and suppresses interventions despite high activity levels that might otherwise suggest overload.
        """

        # Define the scenario
        # Flow State:
        # - High Video Activity (typing, moving head, but focused)
        # - Low/Steady Audio (typing sounds, instrumental music) -> Handled by VAD not flagging speech?
        #   Actually, for this test, we simulate "Low Audio Level" to be safe, or "Non-Speech Audio".
        #   The MockAudioSensor in ReplayHarness typically falls back to RMS.
        #   To simulate "No Speech", we rely on the LMM Mock seeing the context and saying "Focus: High".

        scenario = [
            # Step 1: User enters flow. High activity (typing), Low audio.
            # Expectation: State updates to High Focus. No intervention.
            {
                "description": "Step 1: Entering Flow (High Activity, Low Audio)",
                "input": {
                    "audio_level": 0.05, # Quiet
                    "video_activity": 25.0 # High activity (above default 20.0 threshold)
                },
                "expected_outcome": {
                    "visual_context": ["typing", "focused_on_screen"],
                    "state_estimation": {"focus": 80, "arousal": 60, "overload": 20}, # High Focus
                    "intervention": None
                }
            },
            # Step 2: Deep Flow. High activity continues.
            # Normally, sustained high activity > threshold might trigger "high_video_activity".
            # LogicEngine *will* trigger LMM analysis because video_activity > threshold.
            # BUT, the LMM (mocked) sees "focused_on_screen" and High Focus state,
            # so it should NOT suggest an intervention.
            {
                "description": "Step 2: Deep Flow (Sustained High Activity)",
                "input": {
                    "audio_level": 0.05,
                    "video_activity": 30.0 # Very high activity
                },
                "expected_outcome": {
                    "visual_context": ["typing", "coding", "focused"],
                    "state_estimation": {"focus": 90, "arousal": 65, "overload": 25},
                    "intervention": None
                }
            },
            # Step 3: Peak Flow.
            {
                "description": "Step 3: Peak Flow (High Activity continues)",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 25.0
                },
                "expected_outcome": {
                    "visual_context": ["typing", "coding"],
                    "state_estimation": {"focus": 95, "arousal": 70, "overload": 30},
                    "intervention": None
                }
            }
        ]

        # Initialize Harness
        harness = ReplayHarness()

        # Override LogicEngine threshold to ensure our input triggers the check
        # (Default is 20.0, our input is 25.0, so it will trigger "high_video_activity")
        harness.logic_engine.video_activity_threshold_high = 20.0

        # Run Scenario
        results = harness.run_scenario(scenario)
        harness.print_report(results)

        # Assertions
        self.assertEqual(results['total_steps'], 3)

        # Verify all steps succeeded (Meaning NO intervention was triggered)
        for i, res in enumerate(results['step_results']):
            self.assertTrue(res['success'], f"Step {i+1} failed: {res.get('actual')}")

if __name__ == '__main__':
    unittest.main()
