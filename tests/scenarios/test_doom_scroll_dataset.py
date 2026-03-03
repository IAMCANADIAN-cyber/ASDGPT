import unittest
import sys
import os
import json
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Mock pyautogui before importing tools.replay_harness which imports logic_engine which imports music_interface
sys.modules['pyautogui'] = MagicMock()
sys.modules['mouseinfo'] = MagicMock()

from tools.replay_harness import ReplayHarness
import config

class TestDoomScrollDataset(unittest.TestCase):
    def test_doom_scroll_json(self):
        """
        Tests that the system passes the 'datasets/doom_scroll.json' scenario.
        """
        json_path = os.path.join(os.path.dirname(__file__), '../../datasets/doom_scroll.json')

        if not os.path.exists(json_path):
            self.skipTest(f"Dataset not found: {json_path}")

        harness = ReplayHarness(dataset_path=json_path)
        results = harness.run()
        harness.print_report(results)

        self.assertGreater(results['total_events'], 0, "No events loaded from JSON")
        # Step 9 and 10 trigger intervention. 10 steps total.
        self.assertEqual(results['correct_triggers'], results['total_events'],
                         f"Failed events: {results['total_events'] - results['correct_triggers']}")

if __name__ == '__main__':
    unittest.main()
