import re
import datetime
import argparse
import os
import ast

def parse_log_line(line):
    """
    Parses a single log line.
    Expected format: ISO_TIMESTAMP [LEVEL] MESSAGE
    """
    # Regex to capture timestamp, level, and message
    # 2024-05-24T10:00:00.123456 [INFO] Message content...
    match = re.match(r"^([\d\-T:\.]+) \[(\w+)\] (.*)$", line)
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

            elif "Intervention" in msg and "initiated." in msg:
                event_type = "intervention_start"
                details = msg

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

    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"])

    start_time = events[0]["timestamp"]
    end_time = events[-1]["timestamp"]
    duration = end_time - start_time

    # Statistics
    trigger_counts = {}
    intervention_counts = 0
    feedback_counts = {"helpful": 0, "unhelpful": 0}
    error_counts = 0

    for e in events:
        if e["type"] == "trigger":
            reason = e["details"].replace("LMM Triggered: ", "")
            trigger_counts[reason] = trigger_counts.get(reason, 0) + 1
        elif e["type"] == "intervention_start":
            intervention_counts += 1
        elif e["type"] == "feedback" and e["payload"]:
            val = e["payload"].get("feedback_value", "unknown")
            feedback_counts[val] = feedback_counts.get(val, 0) + 1
        elif e["type"] == "error":
            error_counts += 1

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# ASDGPT Correlation Timeline\n\n")
        f.write(f"**Log Analysis Range:** {start_time} to {end_time} ({duration})\n\n")

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
            # Date header
            event_date = e["timestamp"].date()
            if event_date != current_date:
                f.write(f"\n### {event_date}\n")
                current_date = event_date

            time_str = e["timestamp"].strftime("%H:%M:%S")
            icon = "🔹"
            if e["type"] == "error": icon = "🔴"
            elif e["type"] == "intervention_start": icon = "⚡"
            elif e["type"] == "feedback": icon = "👍" if "helpful" in e["details"].lower() and "unhelpful" not in e["details"].lower() else "👎"
            elif e["type"] == "mode_change": icon = "🔄"
            elif e["type"] == "trigger": icon = "🧠"

            # Format payload if present for extra detail
            extra = ""
            if e["payload"]:
                 # specialized formatting for feedback
                 if e["type"] == "feedback":
                     delta = e["payload"].get("time_delta_seconds", "?")
                     extra = f" (after {delta}s)"

            f.write(f"- `{time_str}` {icon} **{e['type'].upper()}**: {e['details']}{extra}\n")

    print(f"Timeline report generated at: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate a correlation timeline from ASDGPT logs.")
    parser.add_argument("--log", type=str, default="acr_app.log", help="Path to the log file.")
    parser.add_argument("--output", type=str, default="user_data/timeline_report.md", help="Path to the output Markdown file.")

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Parsing log file: {args.log}")
    events = process_log_file(args.log)
    print(f"Found {len(events)} significant events.")

    generate_markdown_report(events, args.output)

if __name__ == "__main__":
    main()
