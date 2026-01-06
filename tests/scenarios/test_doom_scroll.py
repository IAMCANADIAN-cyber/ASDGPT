
import unittest
import sys
import os
import json
import numpy as np
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
import config

class TestDoomScrollScenario(unittest.TestCase):
    def setUp(self):
        # Create a temporary scenario file
        self.scenario_file = "temp_doom_scroll_scenario.json"

        # Scenario:
        # 1. Phone usage detected (Count 1) -> No Intervention
        # 2. Phone usage detected (Count 2) -> No Intervention
        # 3. Phone usage detected (Count 3) -> Doom Scroll Breaker!
        # 4. No phone usage -> Count resets? (Verified in other tests, here we verify trigger)

        # Note: logic_engine checks >= doom_scroll_trigger_threshold (default 3)
        # It triggers on the 3rd event.

        self.events = [
            {
                "id": "doom_1",
                "description": "Phone usage 1",
                "input": {"audio_level": 0.1, "video_activity": 5.0},
                "expected_outcome": {
                    "visual_context": ["phone_usage"],
                    "intervention": None
                }
            },
            {
                "id": "doom_2",
                "description": "Phone usage 2",
                "input": {"audio_level": 0.1, "video_activity": 5.0},
                "expected_outcome": {
                    "visual_context": ["phone_usage"],
                    "intervention": None
                }
            },
            {
                "id": "doom_3",
                "description": "Phone usage 3 (Trigger)",
                "input": {"audio_level": 0.1, "video_activity": 5.0},
                "expected_outcome": {
                    "visual_context": ["phone_usage"],
                    "intervention": "doom_scroll_breaker"
                }
            }
        ]

        with open(self.scenario_file, 'w') as f:
            json.dump(self.events, f)

    def tearDown(self):
        if os.path.exists(self.scenario_file):
            os.remove(self.scenario_file)

    def test_doom_scroll_trigger(self):
        print("\n--- Testing Doom Scroll Persistence Logic ---")
        harness = ReplayHarness(self.scenario_file)

        # Ensure we are testing with the default threshold of 3
        harness.logic_engine.doom_scroll_trigger_threshold = 3

        results = harness.run()
        harness.print_report(results)

        self.assertEqual(results["total_events"], 3)
        self.assertEqual(results["correct_triggers"], 3, "All events should match expected outcomes")
        self.assertEqual(results["false_positives"], 0)
        self.assertEqual(results["false_negatives"], 0)

        # Verify specific intervention logic was hit
        # The harness verifies "expected_outcome.intervention" matches "actual_intervention.type"
        # Event 3 expects "doom_scroll_breaker". If correct_triggers is 3, it worked.

if __name__ == '__main__':
    unittest.main()
