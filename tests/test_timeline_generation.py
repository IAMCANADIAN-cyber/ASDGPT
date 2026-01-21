import unittest
import os
import shutil
import tempfile
import datetime
import shutil
import json
import sys

# Ensure tools can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.generate_timeline import parse_events, generate_markdown

class TestTimelineGeneration(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.events_file = os.path.join(self.test_dir, "test_events.jsonl")
        self.output_file = os.path.join(self.test_dir, "timeline.md")

        # Generate sample events
        self.sample_events = [
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "event_type": "lmm_trigger",
                "payload": {"reason": "high_audio_level"}
            },
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "event_type": "state_update",
                "payload": {"arousal": 60, "overload": 10, "focus": 40}
            },
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "event_type": "intervention_start",
                "payload": {"type": "breathing", "id": "box_breathing"}
            },
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "event_type": "user_feedback",
                "payload": {"intervention_type": "box_breathing", "feedback_value": "helpful"}
            }
        ]

        with open(self.events_file, "w", encoding='utf-8') as f:
            for event in self.sample_events:
                f.write(json.dumps(event) + "\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_events(self):
        events = parse_events(self.events_file)
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0]["event_type"], "lmm_trigger")
        self.assertEqual(events[1]["payload"]["arousal"], 60)

    def test_report_generation(self):
        # Run the generator function
        events = parse_events(self.events_file)
        generate_markdown(events, self.output_file)

        # Verify output file exists
        self.assertTrue(os.path.exists(self.output_file))

        # Verify content
        with open(self.output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check basic content presence
            self.assertIn("high_audio_level", content)

    def test_empty_file(self):
        empty_file = os.path.join(self.test_dir, "empty.jsonl")
        with open(empty_file, 'w', encoding='utf-8') as f:
            pass
        events = parse_events(empty_file)
        self.assertEqual(len(events), 0)

    def test_malformed_json(self):
        bad_file = os.path.join(self.test_dir, "bad.jsonl")
        with open(bad_file, 'w', encoding='utf-8') as f:
            f.write("{broken_json\n")
            f.write(json.dumps(self.sample_events[0]) + "\n")

        events = parse_events(bad_file)
        # Should skip the bad line and read the good one
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "lmm_trigger")

if __name__ == "__main__":
    unittest.main()
