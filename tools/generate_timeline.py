import os
import re
import datetime
import argparse
import json
import sys
from typing import List, Dict, Any

# Ensure we can import modules from the project root if needed
# (though for this standalone tool, we might not strictly need it if we pass args)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class TimelineGenerator:
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.events: List[Dict[str, Any]] = []

    def parse_log(self):
        """Parses the log file and extracts relevant events."""
        if not os.path.exists(self.log_file_path):
            print(f"Error: Log file not found at {self.log_file_path}")
            return

        with open(self.log_file_path, 'r') as f:
            for line in f:
                self._parse_line(line)

    def _parse_line(self, line: str):
        # Expected format: 2026-01-02T09:37:24.486527 [LEVEL] Message
        # Regex to capture timestamp, level, and message
        match = re.match(r'^([\d\-T:\.]+)\s+\[(\w+)\]\s+(.*)$', line.strip())
        if not match:
            return

        timestamp_str, level, message = match.groups()
        try:
            timestamp = datetime.datetime.fromisoformat(timestamp_str)
        except ValueError:
            return # Skip if timestamp format is invalid

        # Classify events based on message content
        event = {
            "timestamp": timestamp,
            "level": level,
            "raw_message": message,
            "type": "generic",
            "details": {}
        }

        if "Triggering LMM analysis" in message:
            event["type"] = "lmm_trigger"
            # Extract reason if possible
            reason_match = re.search(r'Reason: ([\w_]+)', message)
            if reason_match:
                event["details"]["reason"] = reason_match.group(1)

        elif "StateEngine: Updated state to" in message:
            event["type"] = "state_update"
            # Extract state dict
            try:
                state_str = message.split("Updated state to ", 1)[1]
                # Allow for simple eval of dict string (safe enough for local logs)
                # or better, json.loads if valid json (it uses single quotes in logs usually)
                import ast
                state_dict = ast.literal_eval(state_str)
                event["details"]["state"] = state_dict
            except Exception:
                pass

        elif "LMM suggested intervention:" in message:
            event["type"] = "intervention_suggestion"
            try:
                sugg_str = message.split("LMM suggested intervention: ", 1)[1]
                import ast
                sugg_dict = ast.literal_eval(sugg_str)
                event["details"]["suggestion"] = sugg_dict
            except Exception:
                pass

        elif "InterventionEngine: Starting" in message or "Intervention (" in message and ": Started" in message:
             event["type"] = "intervention_start"
             # Try to extract type/message
             # "Intervention (Type: box_breathing): Started."
             type_match = re.search(r'Type: ([\w_]+)', message)
             if type_match:
                 event["details"]["intervention_type"] = type_match.group(1)

        elif "Event: user_feedback" in message:
            event["type"] = "user_feedback"
            # Extract payload
            try:
                payload_str = message.split("| Payload: ", 1)[1]
                import ast
                payload = ast.literal_eval(payload_str)
                event["details"] = payload
            except Exception:
                pass

        elif "LogicEngine Notification: Mode changed" in message:
            event["type"] = "mode_change"
            # "Mode changed from active to snoozed"
            change_match = re.search(r'from (\w+) to (\w+)', message)
            if change_match:
                event["details"]["old_mode"] = change_match.group(1)
                event["details"]["new_mode"] = change_match.group(2)

        self.events.append(event)

    def generate_report(self, output_file: str):
        """Generates a Markdown timeline report."""
        if not self.events:
            print("No events found to report.")
            return

        # Sort events by timestamp
        self.events.sort(key=lambda x: x["timestamp"])

        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_file, 'w') as f:
            f.write("# ASDGPT Event Timeline\n\n")
            f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Source Log:** {self.log_file_path}\n\n")

            f.write("| Timestamp | Event Type | Details |\n")
            f.write("| --- | --- | --- |\n")

            for event in self.events:
                ts = event["timestamp"].strftime("%H:%M:%S.%f")[:-3]
                e_type = event["type"]
                details_str = ""

                if e_type == "lmm_trigger":
                    details_str = f"**Trigger:** {event['details'].get('reason', 'unknown')}"
                elif e_type == "state_update":
                    state = event["details"].get("state", {})
                    # Format state compactly: A:50 O:20 ...
                    state_compact = ", ".join([f"{k[0].upper()}:{v}" for k, v in state.items()])
                    details_str = f"**State Update:** {state_compact}"
                elif e_type == "intervention_suggestion":
                    sugg = event["details"].get("suggestion", {})
                    details_str = f"**Suggestion:** {sugg.get('type') or sugg.get('id')} - \"{sugg.get('message', '')[:30]}...\""
                elif e_type == "intervention_start":
                    details_str = f"**Intervention Started:** {event['details'].get('intervention_type', 'unknown')}"
                elif e_type == "user_feedback":
                    details_str = f"**Feedback:** {event['details'].get('feedback_value', 'unknown')} on {event['details'].get('intervention_type')}"
                elif e_type == "mode_change":
                    details_str = f"**Mode:** {event['details'].get('old_mode')} -> {event['details'].get('new_mode')}"
                else:
                    details_str = event["raw_message"]

                # Escape pipes in details for markdown table
                details_str = details_str.replace("|", "\\|")

                f.write(f"| {ts} | {e_type} | {details_str} |\n")

        print(f"Timeline report generated at: {output_file}")

if __name__ == "__main__":
    # Attempt to import config for defaults, but be robust if it fails
    default_log = "acr_app.log"
    try:
        import config
        if hasattr(config, 'LOG_FILE'):
            default_log = config.LOG_FILE
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Generate a timeline report from ASDGPT logs.")
    parser.add_argument("--log", type=str, default=default_log, help="Path to the log file.")
    parser.add_argument("--output", type=str, default="user_data/timeline_report.md", help="Path to the output markdown file.")

    args = parser.parse_args()

    generator = TimelineGenerator(args.log)
    generator.parse_log()
    generator.generate_report(args.output)
import json
import os
import argparse
from datetime import datetime

def parse_events(events_file):
    events = []
    if not os.path.exists(events_file):
        return []

    with open(events_file, 'r') as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events

def generate_markdown(events, output_file):
    if not events:
        print("No events found.")
        return

    # Sort events by timestamp
    events.sort(key=lambda x: x['timestamp'])

    markdown_content = "# ACR Timeline Report\n\n"
    markdown_content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    current_date = ""

    for event in events:
        ts = datetime.fromisoformat(event['timestamp'])
        date_str = ts.strftime('%Y-%m-%d')
        time_str = ts.strftime('%H:%M:%S')

        if date_str != current_date:
            markdown_content += f"## {date_str}\n\n"
            markdown_content += "| Time | Event Type | Details |\n"
            markdown_content += "| --- | --- | --- |\n"
            current_date = date_str

        event_type = event['event_type']
        payload = event['payload']

        # Format payload for readability
        details = ""
        if event_type == "state_update":
            details = ", ".join([f"{k}: {v}" for k, v in payload.items()])
        elif event_type == "lmm_trigger":
            details = f"Reason: {payload.get('reason', 'unknown')}"
        elif event_type == "intervention_start":
            details = f"Type: {payload.get('type')}, ID: {payload.get('id', 'N/A')}"
        elif event_type == "user_feedback":
            details = f"Rating: **{payload.get('feedback_value', '').upper()}** for {payload.get('intervention_type', 'unknown')}"
        else:
            details = str(payload)

        markdown_content += f"| {time_str} | **{event_type}** | {details} |\n"

    with open(output_file, 'w') as f:
        f.write(markdown_content)

    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate timeline report from ACR events.")
    parser.add_argument("--events", default="user_data/events.jsonl", help="Path to events.jsonl")
    parser.add_argument("--output", default="user_data/timeline_report.md", help="Path to output markdown file")

    args = parser.parse_args()

    events = parse_events(args.events)
    generate_markdown(events, args.output)
