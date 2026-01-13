import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness

class TestPanicAttackScenario(unittest.TestCase):
    def test_panic_attack_trajectory(self):
        """
        Tests that the system correctly identifies a 'panic attack' trajectory
        (Escalating -> Critical) and triggers the appropriate intervention ('meltdown_prevention').
        """

        # Define the scenario
        scenario = [
            # Phase 1: Normal State
            # Baseline: Low arousal, neutral mood.
            {
                "description": "Phase 1: Normal State",
                "input": {
                    "audio_level": 0.05,
                    "video_activity": 5.0
                },
                "expected_outcome": {
                    "state_estimation": {
                        "arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50
                    },
                    "visual_context": ["sitting_quietly"],
                    "intervention": None
                }
            },
            # Phase 2: Escalating
            # Increasing arousal, signs of distress.
            # LMM might note "shallow breathing" or "fidgeting".
            {
                "description": "Phase 2: Escalating (Arousal 70)",
                "input": {
                    "audio_level": 0.2, # Slightly higher audio (breathing/movement)
                    "video_activity": 20.0 # More movement
                },
                "expected_outcome": {
                    "state_estimation": {
                        "arousal": 70, "overload": 40, "focus": 30, "energy": 60, "mood": 40
                    },
                    "visual_context": ["fidgeting", "pacing"],
                    # Maybe a gentle nudge, or nothing yet if threshold not met.
                    # Let's assume no intervention for this intermediate step to test escalation.
                    "intervention": None
                }
            },
            # Phase 3: Critical
            # High arousal, overload. Panic indicators.
            # Expect 'meltdown_prevention' or 'box_breathing'.
            {
                "description": "Phase 3: Critical (Arousal 90)",
                "input": {
                    "audio_level": 0.6, # High audio (gasping/rapid breathing)
                    "video_activity": 50.0 # High movement (rocking/hands on head)
                },
                "expected_outcome": {
                    "state_estimation": {
                        "arousal": 90, "overload": 90, "focus": 10, "energy": 80, "mood": 20
                    },
                    "visual_context": ["hands_on_head", "hyperventilating", "rocking"],
                    "intervention": "meltdown_prevention"
                }
            },
            # Phase 4: Recovery (Post-Intervention)
            # Arousal dropping.
            {
                "description": "Phase 4: Recovery (Arousal 60)",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 5.0
                },
                "expected_outcome": {
                    "state_estimation": {
                        "arousal": 60, "overload": 30, "focus": 40, "energy": 40, "mood": 40
                    },
                    "visual_context": ["sitting_still", "breathing_deeply"],
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
        self.assertEqual(results['total_steps'], 4)

        # Check critical step (Index 2)
        critical_step = results['step_results'][2]
        self.assertTrue(critical_step['success'], f"Critical step failed. Expected: {critical_step['expected']}, Got: {critical_step['actual']}")

        # Check recovery step (Index 3)
        recovery_step = results['step_results'][3]
        self.assertTrue(recovery_step['success'], "Recovery step failed. Should have no intervention.")

if __name__ == '__main__':
    unittest.main()
