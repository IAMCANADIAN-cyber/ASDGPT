import unittest
import os
import sys
import json
import tempfile
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.replay_harness import ReplayHarness

class TestReplayReliability(unittest.TestCase):
    def setUp(self):
        # Create a temporary dataset for testing
        self.test_events = [
            {
                "id": "test_silence",
                "description": "Test Silence",
                "input": {
                    "audio_level": 0.0,
                    "video_activity": 0.0
                },
                "expected_outcome": {
                    "state_change": {"arousal": "decrease"},
                    "intervention": None
                }
            },
            {
                "id": "test_noise",
                "description": "Test Noise Trigger",
                "input": {
                    "audio_level": 0.8,
                    "video_activity": 0.0
                },
                "expected_outcome": {
                    "state_change": {"arousal": "increase"},
                    "intervention": "noise_alert"
                }
            }
        ]

        self.temp_dataset_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(self.test_events, self.temp_dataset_file)
        self.temp_dataset_file.close()

    def tearDown(self):
        os.remove(self.temp_dataset_file.name)
        if os.path.exists("replay_log.txt"):
            try:
                os.remove("replay_log.txt")
            except:
                pass

    def test_replay_harness_reliability(self):
        """
        Verifies that the ReplayHarness correctly processes a known dataset
        with 100% accuracy using the synchronous logic engine.
        """
        harness = ReplayHarness(self.temp_dataset_file.name)
        results = harness.run()

        self.assertEqual(results['total_events'], 2)
        self.assertEqual(results['correct_triggers'], 2)
        self.assertEqual(results['false_positives'], 0)
        self.assertEqual(results['false_negatives'], 0)

        print("TestReplayReliability: Replay harness verified with 100% accuracy on test set.")

if __name__ == '__main__':
    unittest.main()
