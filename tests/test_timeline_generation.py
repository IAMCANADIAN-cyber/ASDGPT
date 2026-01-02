import unittest
import os
import shutil
import tempfile
from tools.generate_timeline import process_log_file, generate_markdown_report

class TestTimelineGeneration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.test_dir, "test_acr.log")
        self.output_file = os.path.join(self.test_dir, "timeline.md")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_dummy_log(self):
        content = """2024-05-24T10:00:00.000000 [INFO] ACR Application Initializing...
2024-05-24T10:00:05.000000 [INFO] Triggering LMM analysis (Reason: periodic_check)...
2024-05-24T10:00:06.000000 [INFO] LMM suggested intervention: {'type': 'stretch', 'message': 'Stretch now'}
2024-05-24T10:00:07.000000 [INFO] Intervention 'stretch' initiated.
2024-05-24T10:00:20.000000 [EVENT] Event: user_feedback | Payload: {'intervention_message': 'Stretch now', 'intervention_type': 'stretch', 'feedback_value': 'helpful', 'time_delta_seconds': 13.0}
2024-05-24T10:05:00.000000 [WARNING] Audio sensor error: Device unavailable
2024-05-24T10:05:01.000000 [ERROR] One or more sensors have entered an error state.
2024-05-24T10:06:00.000000 [INFO] LogicEngine: Changing mode from active to error
"""
        with open(self.log_file, 'w') as f:
            f.write(content)

    def test_process_log_file(self):
        self.create_dummy_log()
        events = process_log_file(self.log_file)

        # Verify event extraction
        self.assertEqual(len(events), 6, f"Should identify 6 significant events (Trigger, Suggestion, Start, Feedback, Error, ModeChange). Found: {len(events)}")

        self.assertEqual(events[0]["type"], "trigger")
        self.assertEqual(events[0]["details"], "LMM Triggered: periodic_check")

        self.assertEqual(events[1]["type"], "intervention_suggestion")

        self.assertEqual(events[2]["type"], "intervention_start")
        self.assertIn("stretch", events[2]["details"])

        self.assertEqual(events[3]["type"], "feedback")
        self.assertEqual(events[3]["payload"]["feedback_value"], "helpful")

        self.assertEqual(events[4]["type"], "error")

        self.assertEqual(events[5]["type"], "mode_change")
        self.assertIn("LogicEngine: Changing mode", events[5]["details"])

    def test_generate_markdown_report(self):
        self.create_dummy_log()
        events = process_log_file(self.log_file)
        generate_markdown_report(events, self.output_file)

        self.assertTrue(os.path.exists(self.output_file))

        with open(self.output_file, 'r') as f:
            content = f.read()

        # Verify markdown content
        self.assertIn("# ASDGPT Correlation Timeline", content)
        self.assertIn("**Interventions** | 1", content)
        self.assertIn("**Feedback (Helpful)** | 1", content)
        self.assertIn("**periodic_check**: 1", content)
        self.assertIn("🧠 **TRIGGER**: LMM Triggered: periodic_check", content)
        self.assertIn("👍 **FEEDBACK**: Feedback: helpful for 'stretch'", content)
        self.assertIn("🔴 **ERROR**:", content)
        self.assertIn("🔄 **MODE_CHANGE**:", content)

if __name__ == '__main__':
    unittest.main()
