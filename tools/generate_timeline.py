import json
import os
import argparse
import datetime
import sys
import re
import ast
import csv
from typing import List, Dict, Any

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
DEFAULT_CSV_FILE = "user_data/correlation.csv"

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

    # Normalize event structure to match log events if possible, or just keep as is
    # For now, we assume they are compatible or handled by the generator
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
                event_type = "trigger"
                # Extract reason: "Triggering LMM analysis (Reason: high_audio_level)..."
                match = re.search(r"Reason: ([\w_]+)", msg)
                if match:
                    details = f"LMM Triggered: {match.group(1)}"
                    payload = {"reason": match.group(1)}

            elif "LMM suggested intervention:" in msg:
                event_type = "intervention_suggestion"
                details = msg.replace("LMM suggested intervention:", "").strip()
                try:
                    payload = ast.literal_eval(details)
                except:
                    pass

            elif "Intervention" in msg and "initiated." in msg:
                event_type = "intervention_start"
                details = msg
                # Try to extract type
                match_int = re.search(r"Intervention '(.+?)'", msg)
                if match_int:
                    payload = {"type": match_int.group(1)}

            elif "Event: user_feedback" in msg:
                event_type = "feedback"
                # Extract payload: Event: user_feedback | Payload: {...}
                if "| Payload: " in msg:
                    payload_str = msg.split("| Payload: ")[1].strip()
                    try:
                        # Use ast.literal_eval for safe evaluation of python dict string
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
                    state_dict = ast.literal_eval(dict_str)
                    payload = state_dict
                    details = f"State: A:{state_dict.get('arousal')} O:{state_dict.get('overload')}"
                except:
                    details = "State Update (Parse Error)"

            elif level == "ERROR":
                event_type = "error"
                details = msg

            if event_type != "generic":
                events.append({
                    "timestamp": ts,
                    "type": event_type,
                    "details": details,
                    "payload": payload,
                    "level": level
                })

    return events

def generate_markdown_report(events: List[Dict[str, Any]], output_file: str):
    """Generates a Markdown timeline report from parsed events."""

    if not events:
        print("No relevant events found.")
        return

    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Sort events
    events.sort(key=lambda x: x.get('timestamp', datetime.datetime.min))

    start_time = events[0]["timestamp"] if events else datetime.datetime.now()
    end_time = events[-1]["timestamp"] if events else datetime.datetime.now()
    duration = end_time - start_time

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ACR Timeline Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Period:** {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')} ({duration})\n")
        f.write(f"**Total Events:** {len(events)}\n\n")

        f.write("| Time | Event Type | Details |\n")
        f.write("|---|---|---|\n")

        for event in events:
            ts = event.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.datetime.fromisoformat(ts)
                except ValueError:
                    ts = datetime.datetime.min

            time_str = ts.strftime("%H:%M:%S") if isinstance(ts, datetime.datetime) else str(ts)
            etype = event.get("type", "UNKNOWN")
            details = str(event.get("details", ""))

            # Escape pipes
            details = details.replace("|", "\\|")

            f.write(f"| {time_str} | {etype} | {details} |\n")

    print(f"Timeline report generated at: {output_file}")

def generate_correlation_csv(events, output_path):
    if not events:
        return

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Event Type", "Details", "Arousal", "Overload"])

        for event in events:
            row = [
                event.get("timestamp", ""),
                event.get("type", ""),
                event.get("details", ""),
                "", # Arousal
                ""  # Overload
            ]

            payload = event.get("payload")
            if payload and isinstance(payload, dict):
                row[3] = payload.get("arousal", "")
                row[4] = payload.get("overload", "")

            writer.writerow(row)

    print(f"Correlation CSV generated at: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate a timeline report from ACR logs and events.")
    parser.add_argument("--log", default=DEFAULT_LOG_FILE, help="Path to the log file.")
    parser.add_argument("--events", default=None, help="Path to events.jsonl (optional, merged with log events).")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to the output Markdown file.")
    parser.add_argument("--csv", default=DEFAULT_CSV_FILE, help="Path to the output correlation CSV file.")

    args = parser.parse_args()

    all_events = []

    # Process Logs
    print(f"Processing log file: {args.log}")
    log_events = process_log_file(args.log)
    all_events.extend(log_events)

    # Process JSONL Events if provided
    if args.events:
        print(f"Processing events file: {args.events}")
        json_events = parse_events(args.events)
        # Convert JSON events to common format if needed
        # For now, we assume they might just be added or we need to normalize them.
        # Simplification: just assume log analysis is primary for this tool,
        # or that json events have "timestamp" and "event_type" -> "type".
        for je in json_events:
             try:
                 ts = datetime.datetime.fromisoformat(je.get("timestamp"))
             except:
                 ts = datetime.datetime.now()

             all_events.append({
                 "timestamp": ts,
                 "type": je.get("event_type", "generic"),
                 "details": str(je.get("payload", "")),
                 "payload": je.get("payload")
             })

    print(f"Found {len(all_events)} total events.")

    generate_markdown_report(all_events, args.output)
    if args.csv:
        generate_correlation_csv(all_events, args.csv)

if __name__ == "__main__":
    main()
