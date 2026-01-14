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
import config

class TestPanicAttackScenario(unittest.TestCase):
    def test_panic_attack_escalation(self):
        """
        Tests that the system correctly identifies a 'panic attack' or 'meltdown' trajectory
        based on escalating sensor inputs and state estimation, eventually triggering
        the 'meltdown_prevention' intervention.
        """

        # Define the scenario
        # Simulating a user becoming increasingly agitated (High Audio/Video),
        # leading to LMM detecting High Arousal/Overload and suggesting a Tier 3 intervention.

        scenario = [
            # Step 1: Baseline. Calm.
            # Low inputs. Normal state. No intervention.
            {
                "description": "Step 1: Baseline (Calm)",
                "input": {
                    "audio_level": 0.05,
                    "video_activity": 2.0
                },
                "expected_outcome": {
                    "visual_context": ["sitting_quietly"],
                    "state_estimation": {"arousal": 20, "overload": 10, "focus": 60, "energy": 50, "mood": 60},
                    "intervention": None
                }
            },
            # Step 2: Early Signs.
            # Inputs rise (Audio 0.6 is above 0.5 threshold, Video 15 is moderate).
            # State shifts: Arousal rises.
            # LMM might suggest a gentle intervention, or none yet. We'll expect None for this test to show escalation.
            {
                "description": "Step 2: Escalation (Agitation)",
                "input": {
                    "audio_level": 0.6, # Loud breathing or noise
                    "video_activity": 15.0 # Fidgeting
                },
                "expected_outcome": {
                    "visual_context": ["fidgeting", "loud_noise"],
                    "state_estimation": {"arousal": 60, "overload": 40, "focus": 30, "energy": 70, "mood": 40},
                    "intervention": None
                }
            },
            # Step 3: Critical State (Panic).
            # Inputs Very High.
            # State Hits Critical Levels (Arousal > 80, Overload > 80).
            # LMM should suggest 'meltdown_prevention'.
            {
                "description": "Step 3: Critical State (Panic Attack)",
                "input": {
                    "audio_level": 0.9, # Very loud
                    "video_activity": 40.0 # Erratic movement
                },
                "expected_outcome": {
                    "visual_context": ["distress", "erratic_movement"],
                    "state_estimation": {"arousal": 90, "overload": 95, "focus": 10, "energy": 90, "mood": 10},
                    "intervention": "meltdown_prevention"
                }
            }
        ]

        # Initialize Harness
        harness = ReplayHarness()

        # Note: LogicEngine prioritizes reflexive triggers (like doom_scroll_breaker).
        # This scenario relies on the LMM's suggestion being accepted because there are no
        # conflicting reflexive triggers active (e.g. persistent phone usage).

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
        self.assertEqual(results['total_steps'], 3)

        # Check specific steps
        # Step 1: Success (Baseline)
        self.assertTrue(results['step_results'][0]['success'], "Step 1 (Baseline) failed")

        # Step 2: Success (Escalation - verify state update accepted)
        self.assertTrue(results['step_results'][1]['success'], "Step 2 (Escalation) failed")

        # Step 3: Success (Intervention Triggered)
        self.assertTrue(results['step_results'][2]['success'], "Step 3 (Intervention) failed")
        # Note: The mock intervention object structure is {'type': 'meltdown_prevention', 'message': '...'}
        # The key is 'type', not 'id' in the mock LMM response structure used by ReplayHarness
        self.assertEqual(results['step_results'][2]['actual'][0]['type'], "meltdown_prevention", "Wrong intervention triggered")

if __name__ == '__main__':
    unittest.main()
