import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
import config

class TestPanicAttackScenario(unittest.TestCase):
    def test_panic_attack_trajectory(self):
        """
        Tests that the system correctly handles a panic attack trajectory:
        Normal -> Escalating (High Speech Rate) -> Critical (Panic).
        Verifies that high speech rate/pitch variance inputs (via VAD)
        are processed and result in the correct LMM-suggested interventions.
        """

        scenario = [
            # Step 1: Baseline (Calm)
            # Low signals, no intervention expected.
            {
                "description": "Step 1: Baseline - Calm state",
                "input": {
                    "audio_level": 0.05,
                    "video_activity": 0.0
                },
                "input_analysis": {
                    "audio": {
                        "rms": 0.05,
                        "speech_rate": 1.5,
                        "pitch_variance": 5.0,
                        "is_speech": False
                    },
                    "video": {"video_activity": 0.0, "face_detected": True, "face_count": 1}
                },
                "expected_outcome": {
                    "state_change": {"arousal": "stable", "overload": "stable"},
                    "intervention": None
                }
            },
            # Step 2: Escalation (High Speech Rate)
            # Signs of anxiety. LMM should suggest a lower tier intervention.
            # We force an LMM trigger by simulating high enough audio/video or relying on the harness's forced periodic check.
            {
                "description": "Step 2: Escalation - Rapid Speech (Anxiety)",
                "input": {
                    "audio_level": 0.4, # Approaching threshold
                    "video_activity": 10.0
                },
                "input_analysis": {
                    "audio": {
                        "rms": 0.4,
                        "speech_rate": 4.5, # > 4.0 = Anxiety
                        "pitch_variance": 40.0,
                        "is_speech": True
                    },
                    "video": {"video_activity": 10.0, "face_detected": True, "face_count": 1}
                },
                "expected_outcome": {
                    "state_change": {"arousal": "increase", "overload": "increase"},
                    "intervention": "breathing_exercise" # Tier 1 suggestion
                }
            },
            # Step 3: Critical (Panic)
            # High distress. LMM should suggest meltdown prevention.
            {
                "description": "Step 3: Critical - Panic Attack",
                "input": {
                    "audio_level": 0.8, # High audio
                    "video_activity": 30.0 # High movement
                },
                "input_analysis": {
                    "audio": {
                        "rms": 0.8,
                        "speech_rate": 6.0, # Very High
                        "pitch_variance": 80.0, # Erratic
                        "is_speech": True
                    },
                    "video": {"video_activity": 30.0, "face_detected": True, "face_count": 1}
                },
                "expected_outcome": {
                    "state_change": {"arousal": "increase", "overload": "increase"},
                    "intervention": "meltdown_prevention" # Tier 3 suggestion
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

        # Verify all steps succeeded
        for step in results['step_results']:
            self.assertTrue(step['success'], f"Step {step['step']} failed: Expected {step['expected']}, Got {step['actual']}")

if __name__ == '__main__':
    unittest.main()
