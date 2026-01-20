import unittest
import os
import shutil
import tempfile
import datetime
import json
import sys

# Ensure tools can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.generate_timeline import parse_events, generate_markdown_report, parse_log_line, process_log_file

class TestTimelineGeneration(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.events_file = os.path.join(self.test_dir, "test_events.jsonl")
        self.log_file = os.path.join(self.test_dir, "test_app.log")
        self.output_file = os.path.join(self.test_dir, "timeline.md")

        # Generate sample events for JSONL
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
            }
        ]

        with open(self.events_file, "w", encoding='utf-8') as f:
            for event in self.sample_events:
                f.write(json.dumps(event) + "\n")

        # Generate sample log file
        self.sample_logs = [
            f"{datetime.datetime.now().isoformat()} [INFO] LogicEngine initialized.",
            f"{datetime.datetime.now().isoformat()} [INFO] Triggering LMM analysis (Reason: high_audio_level)",
            f"{datetime.datetime.now().isoformat()} [INFO] StateEngine: Updated state to {{'arousal': 60, 'overload': 10}}",
            f"{datetime.datetime.now().isoformat()} [EVENT] Event: user_feedback | Payload: {{'intervention_type': 'breathing', 'feedback_value': 'helpful'}}"
        ]

        with open(self.log_file, "w", encoding='utf-8') as f:
            for line in self.sample_logs:
                f.write(line + "\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_events(self):
        events = parse_events(self.events_file)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_type"], "lmm_trigger")
        self.assertEqual(events[1]["payload"]["arousal"], 60)

    def test_parse_log_line(self):
        line = "2026-01-02T10:00:00.000000 [INFO] Test message"
        parsed = parse_log_line(line)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["message"], "Test message")

        bad_line = "Invalid line format"
        parsed = parse_log_line(bad_line)
        self.assertIsNone(parsed)

    def test_process_log_file(self):
        events = process_log_file(self.log_file)
        # We expect 3 events: Trigger, State Update, Feedback. "LogicEngine initialized" is generic and ignored by process_log_file loop filter.
        # Let's check logic in process_log_file:
        # "LogicEngine initialized" -> event_type="generic".
        # "if event_type != 'generic': events.append(...)"
        # So only specific ones are returned.

        # Triggering LMM analysis -> trigger
        # StateEngine: Updated state -> state_update
        # Event: user_feedback -> feedback

        self.assertEqual(len(events), 3)

        trigger = next((e for e in events if e["type"] == "trigger"), None)
        self.assertIsNotNone(trigger)
        self.assertIn("high_audio_level", trigger["details"])

        feedback = next((e for e in events if e["type"] == "feedback"), None)
        self.assertIsNotNone(feedback)
        self.assertIn("helpful", feedback["details"])

    def test_report_generation(self):
        events = process_log_file(self.log_file)
        generate_markdown_report(events, self.output_file)

        # Verify output file exists
        self.assertTrue(os.path.exists(self.output_file))

        # Verify content
        with open(self.output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("# ACR Timeline Report", content)
            self.assertIn("LMM Triggered: high_audio_level", content)
            self.assertIn("State: A:60", content)
            self.assertIn("Feedback: helpful", content)

if __name__ == "__main__":
    unittest.main()
