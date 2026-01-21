import json
import os
import argparse
from datetime import datetime
import sys
import re
import ast

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

def parse_log_line(line):
    """Parses a log line into a dictionary with timestamp, level, and message."""
    # Pattern: 2026-01-02T10:02:43.797827 [INFO] DataLogger initialized...
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
    """Parses a log file and extracts events."""
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
            payload = {}

            # Detect specific event types
            if "Triggering LMM analysis" in msg:
                event_type = "lmm_trigger"
                # Extract reason
                match = re.search(r"Reason: ([\w_]+)", msg)
                if match:
                    payload["reason"] = match.group(1)

            elif "LMM suggested intervention:" in msg:
                event_type = "intervention_suggestion"
                payload["suggestion"] = msg

            elif "Intervention" in msg and "initiated." in msg:
                event_type = "intervention_start"
                # Intervention 'box_breathing' (Tier 2) initiated.
                match = re.search(r"Intervention '(.+?)'", msg)
                if match:
                    payload["id"] = match.group(1)
                    payload["type"] = match.group(1) # Assuming id is type

            elif "Event: user_feedback" in msg:
                event_type = "user_feedback"
                # Extract payload: Event: user_feedback | Payload: {...}
                if "| Payload: " in msg:
                    payload_str = msg.split("| Payload: ")[1].strip()
                    try:
                        payload = ast.literal_eval(payload_str)
                    except:
                        pass

            elif "LogicEngine: Changing mode from" in msg:
                event_type = "mode_change"
                # Changing mode from active to dnd
                match = re.search(r"from (\w+) to (\w+)", msg)
                if match:
                    payload["old_mode"] = match.group(1)
                    payload["new_mode"] = match.group(2)

            elif "StateEngine: Updated state to" in msg:
                event_type = "state_update"
                try:
                    dict_str = msg.split("Updated state to ")[1]
                    payload = ast.literal_eval(dict_str)
                except:
                    pass

            if event_type != "generic":
                # Standardize event structure
                events.append({
                    "timestamp": ts.isoformat() if isinstance(ts, datetime) else ts,
                    "event_type": event_type,
                    "payload": payload,
                    "details": details # Keep raw details if needed
                })

    return events

def generate_markdown(events, output_file):
    """Generates a Markdown timeline report from the parsed events."""
    if not events:
        print("No events found to report.")
        return

    # Sort events by timestamp
    events.sort(key=lambda x: x.get('timestamp', ''))

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ACR Timeline Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Time | Event Type | Details |\n")
        f.write("|---|---|---|\n")

        for event in events:
            ts_str = event.get('timestamp', '')
            try:
                ts = datetime.fromisoformat(ts_str)
                time_str = ts.strftime("%H:%M:%S")
            except ValueError:
                time_str = ts_str

            etype = event.get("event_type", "UNKNOWN")
            payload = event.get("payload", {})
            details_str = ""

            if etype == "state_update":
                # **Arousal**: 60
                details_parts = []
                for k, v in payload.items():
                    details_parts.append(f"**{k.capitalize()}**: {v}")
                details_str = ", ".join(details_parts)

            elif etype == "intervention_start":
                # **Type**: breathing
                details_str = f"**Type**: {payload.get('type', 'unknown')}"
                if 'id' in payload:
                     details_str += f", **ID**: {payload.get('id')}"

            elif etype == "user_feedback":
                # **Rating**: HELPFUL
                val = str(payload.get("feedback_value", "")).upper()
                details_str = f"**Rating**: {val}"
                if 'intervention_type' in payload:
                    details_str += f" for {payload.get('intervention_type')}"

            elif etype == "lmm_trigger":
                details_str = f"LMM Triggered: {payload.get('reason', 'unknown')}"

            else:
                details_str = str(payload) if payload else str(event.get("details", ""))

            # Escape pipes
            details_str = details_str.replace("|", "\\|")

            f.write(f"| {time_str} | {etype} | {details_str} |\n")

    print(f"Report generated at: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a timeline report from ACR logs/events.")
    parser.add_argument("--events", help="Path to events.jsonl")
    parser.add_argument("--log", help="Path to acr_app.log")
    parser.add_argument("--output", default="user_data/timeline_report.md", help="Path to the output Markdown file.")

    args = parser.parse_args()

    events = []
    if args.events:
        events.extend(parse_events(args.events))

    if args.log:
        events.extend(process_log_file(args.log))

    generate_markdown(events, args.output)
