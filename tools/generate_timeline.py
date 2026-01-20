import json
import os
import argparse
import sys
import datetime
import re
import ast

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import config
    DEFAULT_EVENTS_FILE = getattr(config, 'EVENTS_FILE', 'user_data/events.jsonl')
    DEFAULT_LOG_FILE = getattr(config, 'LOG_FILE', 'acr_app.log')
except ImportError:
    DEFAULT_EVENTS_FILE = 'user_data/events.jsonl'
    DEFAULT_LOG_FILE = 'acr_app.log'

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
                event = json.loads(line)
                # Ensure timestamp is a datetime object
                if isinstance(event.get('timestamp'), str):
                    try:
                        event['timestamp'] = datetime.datetime.fromisoformat(event['timestamp'])
                    except ValueError:
                        pass
                events.append(event)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line[:50]}...")
                continue
    return events

def parse_log_line(line):
    """Parses a log line into a dictionary with timestamp, level, and message."""
    # Pattern: 2026-01-02T10:02:43.797827 [INFO] DataLogger initialized...
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
                event_type = "lmm_trigger"
                match = re.search(r"Reason: ([\w_]+)", msg)
                if match:
                    payload = {"reason": match.group(1)}
                    details = f"LMM Triggered: {match.group(1)}"

            elif "LMM suggested intervention:" in msg:
                event_type = "intervention_suggestion"
                details = msg.replace("LMM suggested intervention:", "").strip()

            elif "Intervention" in msg and "initiated." in msg:
                event_type = "intervention_start"
                details = msg
                # Try to extract ID
                match = re.search(r"Intervention '(.+?)'", msg)
                if match:
                    payload = {"id": match.group(1)}

            elif "Event: user_feedback" in msg:
                event_type = "user_feedback"
                if "| Payload: " in msg:
                    payload_str = msg.split("| Payload: ")[1].strip()
                    try:
                        payload = ast.literal_eval(payload_str)
                        details = f"Feedback: {payload.get('feedback_value')} for '{payload.get('intervention_type')}'"
                    except:
                        details = "Feedback (Payload parse error)"

            elif "LogicEngine: Changing mode from" in msg:
                event_type = "mode_change"
                details = msg

            elif "StateEngine: Updated state to" in msg:
                event_type = "state_update"
                try:
                    dict_str = msg.split("Updated state to ")[1]
                    payload = ast.literal_eval(dict_str)
                    details = f"State Update: {payload}"
                except:
                    pass

            elif level == "ERROR":
                event_type = "error"
                details = msg

            if event_type != "generic":
                events.append({
                    "timestamp": ts,
                    "event_type": event_type, # Standardizing on event_type vs type
                    "type": event_type,       # Keeping both for compatibility if needed
                    "details": details,
                    "payload": payload or {}
                })

    return events

def generate_markdown(events, output_file):
    """Generates a Markdown timeline report from the parsed events."""
    if not events:
        print("No events found to report.")
        return

    # Sort events by timestamp
    events.sort(key=lambda x: x.get('timestamp', datetime.datetime.min))

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ACR Timeline Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Time | Event Type | Details |\n")
        f.write("|---|---|---|\n")

        for event in events:
            ts = event.get('timestamp')
            if isinstance(ts, datetime.datetime):
                time_str = ts.strftime("%H:%M:%S")
            else:
                time_str = str(ts)

            etype = event.get('event_type') or event.get('type') or "UNKNOWN"

            # Format details
            details = event.get('details')
            if not details:
                # Construct from payload if details missing
                payload = event.get('payload', {})
                if etype == "state_update":
                    details = ", ".join([f"**{k.capitalize()}**: {v}" for k, v in payload.items() if isinstance(v, (int, float))])
                elif etype == "lmm_trigger":
                    details = f"Reason: {payload.get('reason')}"
                elif etype == "intervention_start":
                    details = f"ID: {payload.get('id')} Type: {payload.get('type')}"
                elif etype == "user_feedback":
                    details = f"Rating: {payload.get('feedback_value')} on {payload.get('intervention_type')}"
                else:
                    details = str(payload)

            # Escape pipes
            details = str(details).replace("|", "\\|")

            f.write(f"| {time_str} | {etype} | {details} |\n")

    print(f"Report generated at: {output_file}")

# Alias for compatibility with tests if they use this name
generate_markdown_report = generate_markdown

def main():
    parser = argparse.ArgumentParser(description="Generate a timeline report from ACR logs or events.")
    parser.add_argument("--events", default=DEFAULT_EVENTS_FILE, help="Path to events.jsonl")
    parser.add_argument("--log", default=DEFAULT_LOG_FILE, help="Path to log file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to output markdown file")
    parser.add_argument("--source", choices=['events', 'log'], default='events', help="Source to use (events.jsonl or log file)")

    args = parser.parse_args()

    if args.source == 'events':
        print(f"Parsing events file: {args.events}")
        events = parse_events(args.events)
    else:
        print(f"Parsing log file: {args.log}")
        events = process_log_file(args.log)

    print(f"Found {len(events)} events.")
    generate_markdown(events, args.output)

if __name__ == "__main__":
    main()
