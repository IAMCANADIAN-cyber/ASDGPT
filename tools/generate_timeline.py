import os
import re
import datetime
import argparse
import json
import sys
import ast

# Constants
DEFAULT_LOG_FILE = "acr_app.log"
DEFAULT_OUTPUT_FILE = "user_data/timeline_report.md"

def parse_log_line(line):
    """Parses a log line into a dictionary with timestamp, level, and message."""
    # Pattern: 2026-01-02T10:02:43.797827 [INFO] DataLogger initialized...
    # Or: 2026-01-02T10:02:43.797827 [EVENT] Event: user_feedback | Payload: {...}

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
        "message": message
    }

def extract_events(log_file_path):
    events = []

    if not os.path.exists(log_file_path):
        print(f"Error: Log file not found at {log_file_path}")
        return []

    print(f"Reading log file: {log_file_path}")

    with open(log_file_path, 'r') as f:
        for line in f:
            parsed = parse_log_line(line.strip())
            if not parsed:
                continue

            msg = parsed["message"]
            ts = parsed["timestamp"]

            # Categorize interesting events
            event_data = None

            # 1. State Updates
            if "StateEngine updated. Current Smoothed State:" in msg:
                # Format: StateEngine updated. Current Smoothed State: {'arousal': 50, ...}
                try:
                    state_str = msg.split("Current Smoothed State: ")[1]
                    # Use literal_eval instead of json.loads for robust python dict parsing
                    state_data = ast.literal_eval(state_str)
                    event_data = {
                        "type": "State Update",
                        "data": state_data,
                        "timestamp": ts
                    }
                except:
                    pass

            # 2. LMM Triggers
            elif "Triggering LMM analysis" in msg:
                # Format: Triggering LMM analysis (Reason: high_audio_level)...
                reason = "Unknown"
                if "(Reason: " in msg:
                    reason = msg.split("(Reason: ")[1].strip(")...")
                event_data = {
                    "type": "LMM Trigger",
                    "reason": reason,
                    "timestamp": ts
                }

            # 3. Interventions
            elif "Intervention" in msg and "initiated." in msg:
                # Format: Intervention 'box_breathing' (Tier 1) initiated.
                details = msg.replace("Intervention ", "").replace(" initiated.", "")
                event_data = {
                    "type": "Intervention",
                    "details": details,
                    "timestamp": ts
                }

            # 4. User Feedback
            elif "Event: user_feedback" in msg:
                # Format: Event: user_feedback | Payload: {...}
                try:
                    payload_str = msg.split("Payload: ")[1]
                    payload = ast.literal_eval(payload_str)
                    event_data = {
                        "type": "Feedback",
                        "data": payload,
                        "timestamp": ts
                    }
                except:
                    pass

            # 5. Mode Changes
            elif "LogicEngine: Changing mode from" in msg:
                # Format: LogicEngine: Changing mode from active to snoozed
                event_data = {
                    "type": "Mode Change",
                    "details": msg.replace("LogicEngine: ", ""),
                    "timestamp": ts
                }

            if event_data:
                events.append(event_data)

    return events

def generate_markdown(events, output_file):
    if not events:
        print("No significant events found to report.")
        return

    # Sort events by timestamp
    events.sort(key=lambda x: x["timestamp"])

    start_time = events[0]["timestamp"]
    end_time = events[-1]["timestamp"]
    duration = end_time - start_time

    md_lines = []
    md_lines.append(f"# 🧭 ASDGPT Timeline Report")
    md_lines.append(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append(f"**Log Period:** {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')} ({duration})")
    md_lines.append(f"**Total Events:** {len(events)}")
    md_lines.append("\n---")

    current_hour = None

    for event in events:
        ts = event["timestamp"]
        ts_str = ts.strftime("%H:%M:%S")

        # Group by hour header
        if ts.hour != current_hour:
            current_hour = ts.hour
            md_lines.append(f"\n## 🕒 {ts.strftime('%H:00')}")

        icon = "🔹"
        line_content = ""

        if event["type"] == "State Update":
            icon = "🧠"
            data = event["data"]
            # Highlight high arousal/overload/low energy
            highlights = []
            if data.get('arousal', 0) > 70: highlights.append(f"**High Arousal ({data['arousal']})**")
            if data.get('overload', 0) > 70: highlights.append(f"**Overload ({data['overload']})**")
            if data.get('energy', 0) < 30: highlights.append(f"Low Energy ({data['energy']})")

            state_summary = ", ".join([f"{k[:1].upper()}:{v}" for k,v in data.items()])
            line_content = f"**State Update**: `{state_summary}`"
            if highlights:
                line_content += " ⚠️ " + ", ".join(highlights)

        elif event["type"] == "LMM Trigger":
            icon = "🤖"
            line_content = f"**LMM Trigger**: {event.get('reason', 'Unknown')}"

        elif event["type"] == "Intervention":
            icon = "🛡️"
            line_content = f"**Intervention**: {event['details']}"

        elif event["type"] == "Feedback":
            icon = "🗣️"
            data = event["data"]
            feedback_val = data.get('feedback_value', 'Unknown')
            intervention = data.get('intervention_type', 'Unknown')
            line_content = f"**User Feedback**: {feedback_val} for `{intervention}`"

        elif event["type"] == "Mode Change":
            icon = "🔄"
            line_content = f"**System**: {event['details']}"

        md_lines.append(f"- `{ts_str}` {icon} {line_content}")

    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_file, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Report generated at: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate a timeline report from ASDGPT logs.")
    parser.add_argument("--log", default=DEFAULT_LOG_FILE, help="Path to the log file.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to the output markdown file.")

    args = parser.parse_args()

    events = extract_events(args.log)
    generate_markdown(events, args.output)

if __name__ == "__main__":
    main()
