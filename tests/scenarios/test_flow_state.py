import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
import config

class TestFlowStateScenario(unittest.TestCase):
    def test_flow_state_trajectory(self):
        """
        Tests that the system correctly distinguishes 'Flow State' (High Activity, High Focus)
        from 'Overload' or 'Distress'.

        Verifies that even with high video/audio activity, if the LMM interprets it as
        'High Focus/Flow', no intervention is triggered.
        """

        scenario = [
            # Step 1: Entering Flow (Moderate Activity, Focus Rising)
            {
                "description": "Step 1: Entering Flow - Moderate activity, focus increasing",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 15.0 # Moderate movement (e.g. typing)
                },
                "input_analysis": {
                    "audio": {
                        "rms": 0.1,
                        "speech_rate": 0.0,
                        "pitch_variance": 2.0,
                        "is_speech": False
                    },
                    "video": {"video_activity": 15.0, "face_detected": True, "face_count": 1}
                },
                "expected_outcome": {
                    "state_estimation": {"focus": 70, "arousal": 40, "overload": 10},
                    "intervention": None
                }
            },
            # Step 2: Deep Flow (High Activity, High Focus)
            # LogicEngine will likely trigger "high_video_activity" analysis here.
            # We must ensure that despite the trigger, the *outcome* is NO INTERVENTION.
            {
                "description": "Step 2: Deep Flow - High activity (intense typing/working), High Focus",
                "input": {
                    "audio_level": 0.2, # Keyboarding noise
                    "video_activity": 45.0 # High movement
                },
                "input_analysis": {
                    "audio": {
                        "rms": 0.2,
                        "speech_rate": 0.0,
                        "pitch_variance": 5.0,
                        "is_speech": False
                    },
                    "video": {"video_activity": 45.0, "face_detected": True, "face_count": 1}
                },
                "expected_outcome": {
                    "state_estimation": {"focus": 90, "arousal": 60, "overload": 20}, # High arousal but manageable
                    "intervention": None
                }
            },
            # Step 3: Sustained Flow (Continued High Activity)
            {
                "description": "Step 3: Sustained Flow - Continued high activity",
                "input": {
                    "audio_level": 0.2,
                    "video_activity": 40.0
                },
                "input_analysis": {
                    "audio": {
                        "rms": 0.2,
                        "speech_rate": 0.0,
                        "pitch_variance": 5.0,
                        "is_speech": False
                    },
                    "video": {"video_activity": 40.0, "face_detected": True, "face_count": 1}
                },
                "expected_outcome": {
                    "state_estimation": {"focus": 95, "arousal": 65, "overload": 25},
                    "intervention": None
                }
            }
        ]

        harness = ReplayHarness()

        # We need to ensure LogicEngine thresholds are set such that Step 2 actually triggers an analysis
        # (to prove the negative: analysis happens, but no intervention).
        # Default mock threshold is 20.0 for video. Step 2 is 45.0.

        results = harness.run_scenario(scenario)
        harness.print_report(results)

        self.assertEqual(results['total_steps'], 3)

        # Verify all steps succeeded (meaning no unexpected interventions occurred)
        for i, step_result in enumerate(results['step_results']):
            self.assertTrue(step_result['success'], f"Step {i+1} failed. {step_result}")

if __name__ == '__main__':
    unittest.main()
