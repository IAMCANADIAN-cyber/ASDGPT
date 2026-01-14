import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness

class TestFlowState(unittest.TestCase):
    def test_flow_state_detection_and_protection(self):
        """
        Verifies that 'Deep Work' / 'Flow State' is detected based on
        Leaning In + Low Audio + Steady Video, and triggers a protective intervention.
        """
        scenario = [
            {
                "description": "Step 1: User leans in, quiet room -> Deep Work Detection",
                "input": {
                    "audio_level": 0.05, # Silence
                    "video_activity": 5.0 # Low/Steady movement (typing)
                },
                "input_analysis": {
                    "audio": {"rms": 0.05, "pitch_variance": 0, "is_speech": False},
                    "video": {
                        "face_detected": True,
                        "face_size_ratio": 0.20, # > 0.15 = Leaning In
                        "vertical_position": 0.4, # Neutral/Upright
                        "head_tilt": 0.0
                    }
                },
                "expected_outcome": {
                    "visual_context": ["person_sitting", "high_focus"],
                    "state_estimation": {"focus": 90, "flow": 90}, # 'flow' isn't a standard key but 'focus' is
                    "intervention": "posture_water_reset" # The flow protection intervention
                }
            }
        ]

        harness = ReplayHarness()
        results = harness.run_scenario(scenario)
        harness.print_report(results)

        # We assert success of the step
        self.assertTrue(results['step_results'][0]['success'], "Flow state detection failed")

if __name__ == '__main__':
    unittest.main()
