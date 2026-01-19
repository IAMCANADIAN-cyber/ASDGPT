import json
import os
import argparse
import datetime
import sys
import re
import ast
from typing import List, Dict, Any, Optional

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

# --- JSONL Event Parsing (New Format) ---

def parse_events(events_file: str) -> List[Dict[str, Any]]:
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

def generate_markdown(events: List[Dict[str, Any]], output_file: str):
    """Generates a Markdown timeline report from the parsed events (JSONL format)."""
    if not events:
        print("No events found to report.")
        return

    # Sort events by timestamp
    # Timestamp format in DataLogger is '%Y-%m-%dT%H:%M:%S.%f' (isoformat)
    events.sort(key=lambda x: x.get('timestamp', ''))

    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    start_time = events[0]["timestamp"]
    end_time = events[-1]["timestamp"]

    # Statistics
    trigger_counts = {}
    intervention_counts = 0
    feedback_counts = {"helpful": 0, "unhelpful": 0}
    error_counts = 0

    for e in events:
        etype = e.get("event_type", "unknown")
        payload = e.get("payload", {})

        if etype == "lmm_trigger":
            reason = payload.get("reason", "unknown")
            trigger_counts[reason] = trigger_counts.get(reason, 0) + 1
        elif etype == "intervention_start":
            intervention_counts += 1
        elif etype == "user_feedback":
            val = payload.get("feedback_value", "unknown")
            feedback_counts[val] = feedback_counts.get(val, 0) + 1
        elif etype == "error":
            error_counts += 1

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ASDGPT Timeline Report (Events)\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Log Range:** {start_time} to {end_time}\n\n")

        f.write("## 📊 Summary Statistics\n")
        f.write("| Metric | Count |\n")
        f.write("| :--- | :--- |\n")
        f.write(f"| **Interventions** | {intervention_counts} |\n")
        f.write(f"| **Errors** | {error_counts} |\n")
        f.write(f"| **Feedback (Helpful)** | {feedback_counts.get('helpful', 0)} |\n")
        f.write(f"| **Feedback (Unhelpful)** | {feedback_counts.get('unhelpful', 0)} |\n")
        f.write("\n")

        f.write("### LMM Triggers\n")
        for reason, count in trigger_counts.items():
            f.write(f"- **{reason}**: {count}\n")
        f.write("\n")

        f.write("## ⏱️ Timeline\n")

        current_date = None
        for e in events:
            ts_str = e.get("timestamp", "")
            try:
                ts = datetime.datetime.fromisoformat(ts_str)
                event_date = ts.date()
                time_str = ts.strftime("%H:%M:%S")
            except ValueError:
                event_date = "Unknown"
                time_str = ts_str

            if event_date != current_date:
                f.write(f"\n### {event_date}\n")
                current_date = event_date

            etype = e.get("event_type", "unknown")
            payload = e.get("payload", {})
            details = ""

            icon = "🔹"
            if etype == "error": icon = "🔴"
            elif etype == "intervention_start": icon = "⚡"
            elif etype == "user_feedback": icon = "👍" if payload.get("feedback_value") == "helpful" else "👎"
            elif etype == "mode_change": icon = "🔄"
            elif etype == "lmm_trigger": icon = "🧠"

            # Format details
            if etype == "lmm_trigger":
                details = f"Trigger: {payload.get('reason')}"
            elif etype == "state_update":
                details = f"State: {payload}"
            elif etype == "intervention_start":
                details = f"Started: {payload.get('type')} ({payload.get('id')})"
            elif etype == "user_feedback":
                details = f"Feedback: {payload.get('feedback_value')} for {payload.get('intervention_type')}"
            else:
                details = str(payload)

            f.write(f"- `{time_str}` {icon} **{etype.upper()}**: {details}\n")

    print(f"Timeline report generated at: {output_file}")


# --- Log Parsing (Legacy/Fallback Format) ---

def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
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

def process_log_file(log_file_path: str) -> List[Dict[str, Any]]:
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
                match = re.search(r"Reason: ([\w_]+)", msg)
                if match:
                    details = f"LMM Triggered: {match.group(1)}"

            elif "LMM suggested intervention:" in msg:
                event_type = "intervention_suggestion"
                details = msg.replace("LMM suggested intervention:", "").strip()

            elif "Intervention" in msg and "initiated." in msg:
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
                        details = "Feedback (Payload parse error)"

            elif "LogicEngine: Changing mode from" in msg:
                event_type = "mode_change"
                details = msg

            elif level == "ERROR":
                event_type = "error"
                details = msg

            elif "StateEngine: Updated state to" in msg:
                event_type = "state_update"
                try:
                    dict_str = msg.split("Updated state to ")[1]
                    payload = ast.literal_eval(dict_str)
                    details = f"State: {payload}"
                except:
                    details = "State Update (Parse Error)"

            if event_type != "generic":
                events.append({
                    "timestamp": ts,
                    "type": event_type,
                    "details": details,
                    "payload": payload
                })

    return events

def generate_markdown_report(events: List[Dict[str, Any]], output_file: str):
    """Generates a Markdown timeline report from parsed log events."""
    if not events:
        print("No significant events found.")
        return

    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ASDGPT Timeline Report (Logs)\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Time | Event Type | Details |\n")
        f.write("|---|---|---|\n")

        for event in events:
            time_str = event["timestamp"].strftime("%H:%M:%S")
            etype = event["type"]
            details_str = str(event["details"]).replace("|", "\\|")

            f.write(f"| {time_str} | {etype} | {details_str} |\n")

    print(f"Report generated at: {output_file}")


def generate_correlation_csv(events: List[Dict[str, Any]], output_path: str):
    if not events:
        return

    import csv

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Event Type", "Details"])

        for event in events:
            row = [
                event["timestamp"].isoformat(),
                event["type"],
                event["details"]
            ]
            writer.writerow(row)

    print(f"Correlation CSV generated at: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate a timeline report from ASDGPT logs or events.")
    parser.add_argument("--events", help="Path to events.jsonl")
    parser.add_argument("--log", help="Path to acr_app.log")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to the output Markdown file.")
    parser.add_argument("--csv", help="Path to output correlation CSV file (only for logs currently).")

    args = parser.parse_args()

    if args.events:
        print(f"Processing events file: {args.events}")
        events = parse_events(args.events)
        generate_markdown(events, args.output)
    elif args.log:
        print(f"Processing log file: {args.log}")
        events = process_log_file(args.log)
        generate_markdown_report(events, args.output)
        if args.csv:
            generate_correlation_csv(events, args.csv)
    else:
        # Default behavior: Try events, then log
        if os.path.exists(DEFAULT_EVENTS_FILE):
             print(f"Processing default events file: {DEFAULT_EVENTS_FILE}")
             events = parse_events(DEFAULT_EVENTS_FILE)
             generate_markdown(events, args.output)
        elif os.path.exists(DEFAULT_LOG_FILE):
             print(f"Processing default log file: {DEFAULT_LOG_FILE}")
             events = process_log_file(DEFAULT_LOG_FILE)
             generate_markdown_report(events, args.output)
        else:
             print("No input files found. Use --events or --log.")

if __name__ == "__main__":
    main()
