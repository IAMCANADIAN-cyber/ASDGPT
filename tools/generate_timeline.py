import re
import datetime
import ast
import argparse
import os
import sys
from typing import List, Dict, Any, Optional

def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single log line and returns a dictionary of event details if relevant.
    """
    # Regex to extract timestamp, level, and message
    # Format: 2024-05-22T10:00:00.123456 [LEVEL] Message
    match = re.match(r'^([\d\-T:\.]+) \[(\w+)\] (.*)$', line)
    if not match:
        return None

    timestamp_str, level, message = match.groups()

    try:
        timestamp = datetime.datetime.fromisoformat(timestamp_str)
    except ValueError:
        return None

    event_type = "UNKNOWN"
    details = {}

    # 1. State Update
    if "StateEngine: Updated state to" in message:
        event_type = "STATE_UPDATE"
        # Extract the dictionary string
        try:
            dict_str = message.split("Updated state to ")[1]
            state_dict = ast.literal_eval(dict_str)
            details = {"state": state_dict}
        except Exception:
            details = {"raw": message}

    # 2. Intervention Initiated
    elif "Intervention" in message and "initiated." in message:
        event_type = "INTERVENTION"
        # Extract intervention type/details
        # Example: Intervention 'box_breathing' (Tier 2) initiated.
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
        # Example: Event: user_feedback | Payload: {...}
        try:
            payload_str = message.split("Payload: ")[1]
            payload = ast.literal_eval(payload_str)
            details = payload
        except Exception:
            details = {"raw": message}

    # 4. LMM Trigger
    elif "Triggering LMM analysis" in message:
        event_type = "LMM_TRIGGER"
        # Example: Triggering LMM analysis (Reason: periodic_check)...
        match_trig = re.search(r"Reason: (.+?)\)", message)
        if match_trig:
            details = {"reason": match_trig.group(1)}
        else:
            details = {"raw": message}

    # 5. LMM Response (Debug/Info)
    elif "LMM suggested intervention:" in message:
        event_type = "LMM_SUGGESTION"
        try:
             # This might be just the suggestion dict part
             suggestion_str = message.split("LMM suggested intervention: ")[1]
             if suggestion_str != "None":
                 details = {"suggestion": ast.literal_eval(suggestion_str)}
             else:
                 return None # Skip 'None' suggestions
        except:
             details = {"raw": message}

    else:
        return None

    return {
        "timestamp": timestamp,
        "type": event_type,
        "details": details,
        "level": level
    }

def generate_markdown_report(events: List[Dict[str, Any]], output_file: str):
    """Generates a Markdown timeline report from parsed events."""

    if not events:
        print("No relevant events found in logs.")
        return

    with open(output_file, 'w') as f:
        f.write("# ACR Timeline Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Time | Event Type | Details |\n")
        f.write("|---|---|---|\n")

        for event in events:
            time_str = event["timestamp"].strftime("%H:%M:%S")
            etype = event["type"]

            # Format details based on type
            details_str = ""
            if etype == "STATE_UPDATE":
                s = event["details"].get("state", {})
                # Format: A:50 O:0 F:50 E:80 M:50
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

    print(f"Report generated at: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate a timeline report from ACR logs.")
    parser.add_argument("--log", default="acr_app.log", help="Path to the log file.")
    parser.add_argument("--output", default="user_data/timeline_report.md", help="Path to the output Markdown file.")

    args = parser.parse_args()

    if not os.path.exists(args.log):
        print(f"Log file not found: {args.log}")
        return

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    events = []
    with open(args.log, 'r') as f:
        for line in f:
            parsed = parse_log_line(line.strip())
            if parsed:
                events.append(parsed)

    generate_markdown_report(events, args.output)

if __name__ == "__main__":
    main()
