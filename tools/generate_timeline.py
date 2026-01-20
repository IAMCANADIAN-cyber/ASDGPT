import json
import os
import argparse
import datetime
import re
import ast
import sys

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

    # Sort events by timestamp
    # Timestamp format in DataLogger is '%Y-%m-%dT%H:%M:%S.%f' (isoformat)
    events.sort(key=lambda x: x.get('timestamp', ''))

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ACR Timeline Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Time | Event Type | Payload |\n")
        f.write("|---|---|---|\n")

        for event in events:
            ts_str = event.get('timestamp', '')
            try:
                ts = datetime.datetime.fromisoformat(ts_str)
                time_str = ts.strftime("%H:%M:%S")
            except ValueError:
                time_str = ts_str

            etype = event.get('event_type', 'unknown')
            payload = event.get('payload', {})

            f.write(f"| {time_str} | {etype} | {str(payload)} |\n")

def parse_log_line(line):
    """Parses a log line into a dictionary with timestamp, level, and message."""
    # Pattern: 2026-01-02T10:02:43.797827 [INFO] DataLogger initialized...
    # Or: 2026-01-02T10:02:43.797827 [EVENT] Event: user_feedback | Payload: {...}

    # Regex to capture timestamp (any non-whitespace at start), level, and message
    match = re.match(r"^(\S+) \[(\w+)\] (.*)", line)
    if not match:
        return None

    timestamp_str, level, message = match.groups()

    try:
        timestamp = datetime.datetime.fromisoformat(timestamp_str)
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
        print(f"Log file not found: {log_file_path}")
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

            # Detect specific event types
            if "Triggering LMM analysis" in msg:
                event_type = "trigger"
                # Extract reason: "Triggering LMM analysis (Reason: high_audio_level)..."
                match = re.search(r"Reason: ([\w_]+)", msg)
                if match:
                    details = f"LMM Triggered: {match.group(1)}"

            elif "LMM suggested intervention:" in msg:
                event_type = "intervention_suggestion"
                details = msg.replace("LMM suggested intervention:", "").strip()

            elif "Intervention" in msg and "initiated" in msg:
                event_type = "intervention_start"
                details = msg

            elif "Event: user_feedback" in msg:
                event_type = "feedback"
                if "| Payload: " in msg:
                    payload_str = msg.split("| Payload: ")[1].strip()
                    try:
                        payload = ast.literal_eval(payload_str)
                        details = f"Feedback: {payload.get('feedback_value')} for '{payload.get('intervention_type')}'"
                    except:
                        details = "Feedback (Parse Error)"

            elif "LogicEngine: Changing mode from" in msg:
                event_type = "mode_change"
                details = msg

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
    if not events:
        print("No significant events found.")
        return

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# ACR Log Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Time | Type | Details |\n")
        f.write("|---|---|---|\n")

        for event in events:
            time_str = event["timestamp"].strftime("%H:%M:%S")
            f.write(f"| {time_str} | {event['type']} | {event['details']} |\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate timeline report.")
    parser.add_argument("--events", help="Path to events.jsonl")
    parser.add_argument("--log", help="Path to acr_app.log")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to output markdown file")

    args = parser.parse_args()

    if args.events:
        events = parse_events(args.events)
        generate_markdown(events, args.output)
    elif args.log:
        events = process_log_file(args.log)
        generate_markdown_report(events, args.output)
    else:
        # Default to default events file
        events = parse_events(DEFAULT_EVENTS_FILE)
        generate_markdown(events, args.output)
