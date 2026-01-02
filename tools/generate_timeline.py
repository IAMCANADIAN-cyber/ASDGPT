import re
import datetime
import os
import ast
import argparse

def parse_log_line(line):
    # Log format: ISO_TIMESTAMP [LEVEL] Message
    # Example: 2024-05-22T10:00:00.123456 [INFO] LogicEngine Notification: Mode changed from active to snoozed

    # Regex to capture timestamp, level, and message
    match = re.match(r"^(\S+) \[(\w+)\] (.*)$", line)
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

def generate_timeline(log_file_path, output_path):
    if not os.path.exists(log_file_path):
        print(f"Log file not found: {log_file_path}")
        return

    events = []

    with open(log_file_path, 'r') as f:
        for line in f:
            parsed = parse_log_line(line.strip())
            if not parsed:
                continue

            msg = parsed["message"]
            timestamp = parsed["timestamp"]

            # Categorize events
            event_type = "INFO"
            details = msg

            if "StateEngine: Updated state to" in msg:
                event_type = "STATE_UPDATE"
                try:
                    # Extract dict string
                    dict_str = msg.split("Updated state to ")[1]
                    # Safe eval
                    state_dict = ast.literal_eval(dict_str)
                    # Format nicely
                    details = f"**State**: A:{state_dict.get('arousal')} E:{state_dict.get('energy')} F:{state_dict.get('focus')} M:{state_dict.get('mood')} O:{state_dict.get('overload')}"
                except:
                    details = "State Update (Parse Error)"

            elif "Intervention" in msg and "initiated" in msg:
                event_type = "INTERVENTION"
                details = f"🚀 **{msg}**"

            elif "Feedback" in msg and "logged for intervention" in msg:
                event_type = "FEEDBACK"
                details = f"🗣️ **{msg}**"

            elif "Triggering LMM analysis" in msg:
                event_type = "LMM_TRIGGER"
                details = f"🤖 {msg}"

            elif "Mode changed from" in msg:
                event_type = "MODE_CHANGE"
                details = f"🔄 {msg}"

            elif "Snooze expired" in msg:
                event_type = "MODE_CHANGE"
                details = f"⏰ {msg}"

            # Filter for significant events only?
            if event_type in ["STATE_UPDATE", "INTERVENTION", "FEEDBACK", "LMM_TRIGGER", "MODE_CHANGE"]:
                events.append({
                    "timestamp": timestamp,
                    "type": event_type,
                    "details": details
                })

    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"])

    # Generate Markdown
    md_lines = ["# ACR Correlation Timeline", "", f"Generated from: `{log_file_path}`", ""]

    if not events:
        md_lines.append("No significant events found.")
    else:
        # Group by hour or just list? List is fine for now.
        md_lines.append("| Time | Type | Details |")
        md_lines.append("| --- | --- | --- |")

        for event in events:
            time_str = event["timestamp"].strftime("%H:%M:%S")
            md_lines.append(f"| {time_str} | {event['type']} | {event['details']} |")

    with open(output_path, 'w') as f:
        f.write("\n".join(md_lines))

    print(f"Timeline report generated at: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a timeline report from ACR logs.")
    parser.add_argument("--log", default="acr_app.log", help="Path to the log file.")
    parser.add_argument("--output", default="user_data/timeline_report.md", help="Path to the output Markdown file.")

    args = parser.parse_args()

    # Ensure output dir exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    generate_timeline(args.log, args.output)
