import os
import sys
import unittest
import tempfile
import datetime
from tools.generate_timeline import parse_log_line, generate_markdown_report

class TestTimelineGeneration(unittest.TestCase):
    def setUp(self):
        # Create a temporary log file
        self.test_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.test_dir, "test_acr.log")
        self.output_file = os.path.join(self.test_dir, "timeline.md")

        # Generate sample logs
        self.logs = [
            f"{datetime.datetime.now().isoformat()} [INFO] Triggering LMM analysis (Reason: high_audio_level)...",
            f"{datetime.datetime.now().isoformat()} [INFO] LMM suggested intervention: {{'id': 'box_breathing'}}",
            f"{datetime.datetime.now().isoformat()} [INFO] StateEngine: Updated state to {{'arousal': 60, 'overload': 10, 'focus': 40, 'energy': 70, 'mood': 50}}",
            f"{datetime.datetime.now().isoformat()} [INFO] Intervention 'box_breathing' (Tier 2) initiated.",
            f"{datetime.datetime.now().isoformat()} [EVENT] Event: user_feedback | Payload: {{'intervention_type': 'box_breathing', 'feedback_value': 'helpful'}}"
        ]

        with open(self.log_file, "w") as f:
            for line in self.logs:
                f.write(line + "\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)

    def test_parse_log_line(self):
        # Test Trigger
        line1 = self.logs[0]
        parsed1 = parse_log_line(line1)
        self.assertEqual(parsed1["type"], "LMM_TRIGGER")
        self.assertEqual(parsed1["details"]["reason"], "high_audio_level")

        # Test State Update
        line3 = self.logs[2]
        parsed3 = parse_log_line(line3)
        self.assertEqual(parsed3["type"], "STATE_UPDATE")
        self.assertEqual(parsed3["details"]["state"]["arousal"], 60)

        # Test Intervention
        line4 = self.logs[3]
        parsed4 = parse_log_line(line4)
        self.assertEqual(parsed4["type"], "INTERVENTION")
        self.assertEqual(parsed4["details"]["intervention_id"], "box_breathing")

    def test_report_generation(self):
        # Run the generator function
        events = []
        with open(self.log_file, 'r') as f:
            for line in f:
                parsed = parse_log_line(line.strip())
                if parsed:
                    events.append(parsed)

        generate_markdown_report(events, self.output_file)

        # Verify output file exists
        self.assertTrue(os.path.exists(self.output_file))

        # Verify content
        with open(self.output_file, 'r') as f:
            content = f.read()
            self.assertIn("# ACR Timeline Report", content)
            self.assertIn("Arousal:60", content)
            self.assertIn("**box_breathing**", content)
            self.assertIn("User rated 'box_breathing': **HELPFUL**", content)

if __name__ == "__main__":
    unittest.main()
