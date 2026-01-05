import unittest
import os
import sys
import json
import tempfile
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.replay_harness import ReplayHarness

class TestDoomScrollScenario(unittest.TestCase):
    def setUp(self):
        # Create a synthetic "Doom Scroll" dataset
        # This simulates a user scrolling on a phone, which might be detected via
        # specific visual context tags (e.g., "phone_usage") or persistent low-arousal/high-focus state?
        # Based on logic_engine.py, it tracks "phone_usage" in context_persistence.
        # It triggers "doom_scroll_breaker" if threshold is reached.

        self.test_events = []

        # Event 1: Phone usage detected (1/3)
        self.test_events.append({
            "id": "doom_scroll_1",
            "description": "Phone usage detected (1/3)",
            "input": {
                "audio_level": 0.1,
                "video_activity": 5.0
            },
            "expected_outcome": {
                # We expect the mock LMM to return "phone_usage" in visual_context
                # But ReplayHarness MockLMM currently doesn't support injecting visual_context easily
                # unless we modify it or the dataset format.
                # Let's see how MockLMM works in tools/replay_harness.py

                # LogicEngine uses lmm_interface.process_data -> analysis
                # MockLMM returns analysis based on expected_outcome.
                # I need to ensure MockLMM can return visual_context.

                "visual_context": ["phone_usage"],
                "intervention": None
            }
        })

        # Event 2: Phone usage detected (2/3)
        self.test_events.append({
            "id": "doom_scroll_2",
            "description": "Phone usage detected (2/3)",
            "input": {
                "audio_level": 0.1,
                "video_activity": 5.0
            },
            "expected_outcome": {
                "visual_context": ["phone_usage"],
                "intervention": None
            }
        })

        # Event 3: Phone usage detected (3/3) -> TRIGGER
        self.test_events.append({
            "id": "doom_scroll_3",
            "description": "Phone usage detected (3/3) - Should Trigger",
            "input": {
                "audio_level": 0.1,
                "video_activity": 5.0
            },
            "expected_outcome": {
                "visual_context": ["phone_usage"],
                "intervention": "doom_scroll_breaker" # The specific intervention ID
            }
        })

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

    def test_doom_scroll_trigger(self):
        """
        Verifies that persistent phone usage triggers the doom_scroll_breaker intervention.
        """
        # I need to modify ReplayHarness's MockLMM to support returning 'visual_context'
        # from the expected_outcome.

        # Since I cannot modify ReplayHarness in this test file easily without monkeypatching,
        # I should probably update ReplayHarness first if it doesn't support this.
        # Let's check ReplayHarness code again.

        harness = ReplayHarness(self.temp_dataset_file.name)

        # Monkeypatch the mock_lmm.process_data to handle visual_context from expectation
        original_process_data = harness.mock_lmm.process_data

        def patched_process_data(video_data=None, audio_data=None, user_context=None):
            analysis = original_process_data(video_data, audio_data, user_context)

            # Inject visual_context if present in expectation
            if harness.mock_lmm.current_expected_outcome:
                vc = harness.mock_lmm.current_expected_outcome.get("visual_context")
                if vc:
                    analysis["visual_context"] = vc
            return analysis

        harness.mock_lmm.process_data = patched_process_data

        results = harness.run()

        # We expect 3 events.
        # 1st: No intervention (Success)
        # 2nd: No intervention (Success)
        # 3rd: Doom Scroll Breaker (Success)

        self.assertEqual(results['total_events'], 3)
        self.assertEqual(results['correct_triggers'], 3)
        self.assertEqual(results['false_positives'], 0)
        self.assertEqual(results['false_negatives'], 0)

if __name__ == '__main__':
    unittest.main()
