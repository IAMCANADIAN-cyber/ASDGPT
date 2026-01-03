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
    match = re.match(r"^(\S+) \[(\w+)\] (.*)$", line)
    if not match:
        return None

    timestamp_str, level, message = match.groups()

    try:
        timestamp = datetime.datetime.fromisoformat(timestamp_str)
    except ValueError:
        return None

    event_type = "generic"
    details = {}
    payload = None

    # 1. State Update
    if "StateEngine: Updated state to" in message:
        event_type = "STATE_UPDATE"
        try:
            dict_str = message.split("Updated state to ")[1]
            state_dict = ast.literal_eval(dict_str)
            details = {"state": state_dict}
        except Exception:
            details = {"raw": message}

    # 2. Intervention Initiated
    elif "Intervention" in message and "initiated." in message:
        event_type = "INTERVENTION"
        match_int = re.search(r"Intervention '(.+?)'(?: \(Tier (\d+)\))? initiated", message)
        if match_int:
            details = {
                "intervention_id": match_int.group(1),
                "tier": match_int.group(2) if match_int.group(2) else "1"
            }
        else:
            details = {"raw": message}

    # 3. User Feedback
    elif level == "EVENT" and "Event: user_feedback" in message:
        event_type = "FEEDBACK"
        try:
            payload_str = message.split("Payload: ")[1]
            payload = ast.literal_eval(payload_str)
            details = payload
        except Exception:
            details = {"raw": message}

    # 4. LMM Trigger
    elif "Triggering LMM analysis" in message:
        event_type = "LMM_TRIGGER"
        match_trig = re.search(r"Reason: (.+?)\)", message)
        if match_trig:
            details = {"reason": match_trig.group(1)}
        else:
            details = {"raw": message}

    # 5. LMM Response (Debug/Info)
    elif "LMM suggested intervention:" in message:
        event_type = "LMM_SUGGESTION"
        try:
             suggestion_str = message.split("LMM suggested intervention: ")[1]
             if suggestion_str != "None":
                 details = {"suggestion": ast.literal_eval(suggestion_str)}
             else:
                 return None
        except:
             details = {"raw": message}

    else:
        return None

    return {
        "timestamp": timestamp,
        "type": event_type,
        "details": details,
        "level": level,
        "payload": payload
    }

def process_log_file(log_file_path):
    events = []
    if not os.path.exists(log_file_path):
        print(f"Log file not found: {log_file_path}")
        return []

    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parsed = parse_log_line(line.strip())
            if parsed:
                events.append(parsed)
    return events

def generate_markdown_report(events, output_path):
    if not events:
        print("No significant events found.")
        return

    with open(output_path, 'w') as f:
        f.write("# ACR Timeline Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Time | Event Type | Details |\n")
        f.write("|---|---|---|\n")

        for event in events:
            time_str = event["timestamp"].strftime("%H:%M:%S")
            etype = event["type"]

            details_str = ""
            if etype == "STATE_UPDATE":
                s = event["details"].get("state", {})
                details_str = f"Arousal:{s.get('arousal')} Overload:{s.get('overload')} Focus:{s.get('focus')} Energy:{s.get('energy')} Mood:{s.get('mood')}"

            elif etype == "INTERVENTION":
                details_str = f"**{event['details'].get('intervention_id')}**"
                if event['details'].get('tier'):
                    details_str += f" (Tier {event['details']['tier']})"

            elif etype == "FEEDBACK":
                val = event["details"].get("feedback_value", "unknown").upper()
                int_type = event["details"].get("intervention_type", "unknown")
                details_str = f"User rated '{int_type}': **{val}**"

            elif etype == "LMM_TRIGGER":
                details_str = f"Reason: {event['details'].get('reason')}"

            elif etype == "LMM_SUGGESTION":
                 sug = event["details"].get("suggestion", {})
                 details_str = f"Proposed: {sug.get('id') or sug.get('type')}"

            else:
                details_str = str(event["details"])

            f.write(f"| {time_str} | {etype} | {details_str} |\n")

    print(f"Report generated at: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate a timeline report from ACR logs.")
    parser.add_argument("--log", default="acr_app.log", help="Path to the log file.")
    parser.add_argument("--output", default="user_data/timeline_report.md", help="Path to the output Markdown file.")

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    events = process_log_file(args.log)
    generate_markdown_report(events, args.output)

if __name__ == "__main__":
    main()
