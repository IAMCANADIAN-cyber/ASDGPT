
import unittest
import os
import sys
import json
import numpy as np
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
from core.logic_engine import LogicEngine

class TestDoomScrollScenario(unittest.TestCase):
    def setUp(self):
        # Create a temporary dataset for Doom Scroll
        self.dataset_path = "tests/scenarios/temp_doom_dataset.json"
        self.events = [
            {
                "id": "doom_scroll_01",
                "description": "User staring at phone, low audio, low movement",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 5.0
                },
                "expected_outcome": {
                    "intervention": None,
                    "visual_context": ["phone_usage"]
                }
            },
            {
                "id": "doom_scroll_02",
                "description": "User still staring at phone",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 2.0
                },
                "expected_outcome": {
                    "intervention": None,
                    "visual_context": ["phone_usage"]
                }
            },
            {
                "id": "doom_scroll_03",
                "description": "User still staring at phone - Trigger Threshold",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 2.0
                },
                "expected_outcome": {
                    "intervention": "doom_scroll_breaker",
                    "visual_context": ["phone_usage"]
                }
            }
        ]
        with open(self.dataset_path, 'w') as f:
            json.dump(self.events, f)

    def tearDown(self):
        if os.path.exists(self.dataset_path):
            os.remove(self.dataset_path)

    def test_doom_scroll_trigger(self):
        # We need to extend the MockLMM in ReplayHarness to support visual_context injection
        # forcing us to subclass or modify ReplayHarness slightly for this test.
        # But wait, ReplayHarness uses MockLMMInterface. logic_engine calls it.

        # Let's instantiate the Harness
        harness = ReplayHarness(self.dataset_path)

        # We need to patch the MockLMM inside the harness to return visual_context
        # The current MockLMM in replay_harness.py doesn't seem to support injecting visual_context from the event expectation
        # It only looks at "state_change" and "intervention".

        # Let's override the mock's process_data method dynamically
        original_process_data = harness.mock_lmm.process_data

        def custom_process_data(video_data=None, audio_data=None, user_context=None):
            # Call original to get base structure
            analysis = original_process_data(video_data, audio_data, user_context)

            # Inject visual context from the current expectation if present
            if harness.mock_lmm.current_expected_outcome:
                vc = harness.mock_lmm.current_expected_outcome.get("visual_context")
                if vc:
                    analysis["visual_context"] = vc

            # Also, if we expect an intervention via reflexive trigger (which happens in LogicEngine),
            # the LMM might return None for suggestion, but LogicEngine will override.
            # However, MockLMM sets "suggestion" based on "intervention" key.
            # For doom scroll, the intervention comes from LogicEngine's persistence, NOT the LMM suggestion necessarily.
            # In the real world, LMM sees "phone_usage" and returns it in visual_context.
            # LogicEngine sees "phone_usage" x3 and triggers "doom_scroll_breaker".

            # So we should ensure LMM does NOT suggest the intervention directly if we want to test the reflexive trigger.
            # But the 'expected_outcome' has "intervention": "doom_scroll_breaker".
            # The MockLMM logic in ReplayHarness currently sets analysis["suggestion"] if "intervention" is in expected_outcome.

            # We want to test LogicEngine's reflexive logic, so we should suppress the LMM suggestion for this test case
            # to prove it came from LogicEngine.

            if analysis.get("suggestion") and analysis["suggestion"]["type"] == "doom_scroll_breaker":
                # Clear it to verify LogicEngine generates it
                analysis["suggestion"] = None

            return analysis

        harness.mock_lmm.process_data = custom_process_data

        # Run the harness
        results = harness.run()

        # Verify
        self.assertEqual(results["correct_triggers"], 3, "Should correctly identify all 3 events")
        self.assertEqual(results["triggered_interventions"], 1, "Should trigger exactly 1 intervention")

if __name__ == '__main__':
    unittest.main()
