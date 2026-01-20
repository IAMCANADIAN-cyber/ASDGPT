import json
import os
import argparse
from datetime import datetime
import sys
import re
import ast

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import config
    DEFAULT_EVENTS_FILE = getattr(config, 'EVENTS_FILE', 'user_data/events.jsonl')
except ImportError:
    DEFAULT_EVENTS_FILE = 'user_data/events.jsonl'
DEFAULT_OUTPUT_FILE = "user_data/timeline_report.md"

def parse_events(events_file):
    """Parses the events.jsonl file into a list of dictionaries."""
    events = []
    if not os.path.exists(events_file):
        print(f"Warning: Events file not found at {events_file}")
        return []

    with open(events_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line[:50]}...")
                continue
    return events

def generate_markdown(events, output_file):
    """Generates a Markdown timeline report from the parsed events."""
    if not events:
        print("No events found to report.")
        return

    events.sort(key=lambda x: x.get('timestamp', ''))

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ACR Timeline Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for event in events:
            ts = event.get('timestamp', 'Unknown Time')
            etype = event.get('event_type', 'Unknown Type')
            payload = event.get('payload', {})

            f.write(f"- **{ts}** - *{etype}*: {payload}\n")

    print(f"Report generated at: {output_file}")

# --- Log Parsing Logic ---

def parse_log_line(line):
    """Parses a log line into a dictionary with timestamp, level, and message."""
    # Pattern: 2026-01-02T10:02:43.797827 [INFO] Message...
    match = re.match(r"^(\S+) \[(\w+)\] (.*)", line)
    if not match:
        return None

    timestamp_str, level, message = match.groups()

    try:
        timestamp = datetime.fromisoformat(timestamp_str)
    except ValueError:
        return None

    return {
        "timestamp": timestamp,
        "level": level,
        "message": message.strip()
    }

def process_log_file(log_file_path):
    events = []
    if not os.path.exists(log_file_path):
        return []

    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parsed = parse_log_line(line)
            if not parsed:
                continue

            ts = parsed["timestamp"]
            msg = parsed["message"]
            level = parsed["level"]

            event_type = "generic"
            details = msg
            payload = None

            if "Triggering LMM analysis" in msg:
                event_type = "trigger"
                match = re.search(r"Reason: ([\w_]+)", msg)
                if match:
                    details = f"LMM Triggered: {match.group(1)}"

            elif "LMM suggested intervention:" in msg:
                event_type = "intervention_suggestion"
                details = msg.replace("LMM suggested intervention:", "").strip()

            elif "Intervention" in msg and "initiated." in msg:
                event_type = "intervention_start"
                match = re.search(r"Intervention '([\w_]+)'", msg)
                if match:
                    itype = match.group(1)
                    details = f"**Type**: {itype}"
                else:
                    details = msg

            elif "Event: user_feedback" in msg:
                event_type = "feedback"
                if "| Payload: " in msg:
                    payload_str = msg.split("| Payload: ")[1].strip()
                    try:
                        payload = ast.literal_eval(payload_str)
                        details = f"**Rating**: {str(payload.get('feedback_value')).upper()}"
                    except:
                        details = "Feedback (Payload parse error)"

            elif "StateEngine: Updated state to" in msg:
                 event_type = "state_update"
                 try:
                     dict_str = msg.split("Updated state to ")[1]
                     payload = ast.literal_eval(dict_str)
                     details = ", ".join([f"**{k.capitalize()}**: {v}" for k, v in payload.items()])
                 except:
                     pass

            elif level == "ERROR":
                event_type = "error"
                details = msg

            if event_type != "generic":
                events.append({
                    "timestamp": ts,
                    "type": event_type,
                    "details": details,
                    "payload": payload
                })
    return events

def generate_markdown_report(events, output_path):
    """Generates markdown report from process_log_file events."""
    if not events:
        print("No significant events found.")
        return

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# ACR Timeline Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for event in events:
            ts = event["timestamp"].strftime("%H:%M:%S")
            etype = event["type"]
            details = event["details"]
            f.write(f"- **{ts}** [{etype.upper()}]: {details}\n")
    print(f"Report generated at: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate timeline report from ACR events.")
    parser.add_argument("--events", default=DEFAULT_EVENTS_FILE, help="Path to events.jsonl")
    parser.add_argument("--log", default="acr_app.log", help="Path to log file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to output markdown file")

    args = parser.parse_args()

    # Prioritize log processing if log exists, else events
    if os.path.exists(args.log):
        print(f"Processing log file: {args.log}")
        log_events = process_log_file(args.log)
        generate_markdown_report(log_events, args.output)
    else:
        print(f"Processing events file: {args.events}")
        events_list = parse_events(args.events)
        generate_markdown(events_list, args.output)
