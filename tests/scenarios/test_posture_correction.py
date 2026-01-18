import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness

class TestPostureCorrectionScenario(unittest.TestCase):
    def test_posture_correction_trajectory(self):
        """
        Tests the system's response to detected bad posture (slouching).

        Steps:
        1. Baseline (Neutral): User sits normally. No intervention.
        2. Slouching Start: User begins to slouch. LMM detects it, but might wait or prioritize monitoring.
        3. Slouching Persists: User continues slouching. LMM suggests 'posture_water_reset'.
        """

        scenario = [
            # Step 1: Baseline (Neutral)
            {
                "description": "Step 1: Baseline - Neutral posture",
                "input": {
                    "audio_level": 0.05,
                    "video_activity": 5.0
                },
                "input_analysis": {
                    "video": {
                        "video_activity": 5.0,
                        "face_detected": True,
                        "posture_state": "neutral",
                        "face_size_ratio": 0.2,
                        "vertical_position": 0.4
                    }
                },
                "expected_outcome": {
                    "state_estimation": {"focus": 50, "energy": 80, "arousal": 50, "overload": 0, "mood": 50},
                    "expected_state": {"focus": 50, "energy": 80, "arousal": 50, "overload": 0, "mood": 50},
                    "intervention": None
                }
            },
            # Step 2: Slouching Start
            {
                "description": "Step 2: Slouching detected - Energy/Focus drop",
                "input": {
                    "audio_level": 0.05,
                    "video_activity": 2.0
                },
                "input_analysis": {
                    "video": {
                        "video_activity": 2.0,
                        "face_detected": True,
                        "posture_state": "slouching",
                        "face_size_ratio": 0.2,
                        "vertical_position": 0.7 # Low in frame
                    }
                },
                "expected_outcome": {
                    "state_estimation": {"focus": 40, "energy": 60, "arousal": 40, "overload": 0, "mood": 45},
                    # Smoothing (History: 50, 50, 50, 50, 40) -> Avg 48
                    # Energy: (80*4 + 60)/5 = 76
                    "expected_state": {"focus": 48, "energy": 76},
                    "intervention": None
                }
            },
            # Step 3: Slouching Persists -> Intervention
            {
                "description": "Step 3: Slouching persists - Intervention Triggered",
                "input": {
                    "audio_level": 0.05,
                    "video_activity": 2.0
                },
                "input_analysis": {
                    "video": {
                        "video_activity": 2.0,
                        "face_detected": True,
                        "posture_state": "slouching",
                        "face_size_ratio": 0.2,
                        "vertical_position": 0.75
                    }
                },
                "expected_outcome": {
                    "state_estimation": {"focus": 30, "energy": 50, "arousal": 30, "overload": 0, "mood": 40},
                    # History: 50, 50, 50, 40, 30 -> Avg 44
                    # Energy: 80, 80, 80, 60, 50 -> Avg 70
                    "expected_state": {"focus": 44, "energy": 70},
                    "intervention": "posture_water_reset"
                }
            }
        ]

        harness = ReplayHarness()
        results = harness.run_scenario(scenario)
        harness.print_report(results)

        self.assertEqual(results['total_steps'], 3)
        for i, step_result in enumerate(results['step_results']):
            self.assertTrue(step_result['success'], f"Step {i+1} failed. Expected: {step_result['expected']}, Got: {step_result['actual']}")

if __name__ == '__main__':
    unittest.main()
