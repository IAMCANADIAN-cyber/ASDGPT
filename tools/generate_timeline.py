import json
import os
import argparse
from datetime import datetime
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
    # We can sort lexicographically since it's ISO, but parsing is safer.
    events.sort(key=lambda x: x.get('timestamp', ''))

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import config
    DEFAULT_EVENTS_FILE = getattr(config, 'EVENTS_FILE', 'user_data/events.jsonl')
except ImportError:
    DEFAULT_EVENTS_FILE = 'user_data/events.jsonl'
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

    markdown_content = "# ACR Timeline Report\n\n"
    markdown_content += f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    markdown_content += f"**Total Events:** {len(events)}\n\n"

    current_date = ""

    for event in events:
        ts_str = event.get('timestamp', '')
        try:
            ts = datetime.fromisoformat(ts_str)
            date_str = ts.strftime('%Y-%m-%d')
            time_str = ts.strftime('%H:%M:%S')
        except ValueError:
            # Fallback for invalid timestamp
            date_str = "Unknown Date"
            time_str = ts_str

        if date_str != current_date:
            markdown_content += f"## {date_str}\n\n"
            markdown_content += "| Time | Event Type | Details |\n"
            markdown_content += "| --- | --- | --- |\n"
            current_date = date_str

        event_type = event.get('event_type', 'unknown')
        payload = event.get('payload', {})

        # Format payload for readability
        details = ""
        if event_type == "state_update":
            # Payload example: {"arousal": 50, "overload": 0...}
            details = ", ".join([f"**{k.capitalize()}**: {v}" for k, v in payload.items()])
        elif event_type == "lmm_trigger":
            # Payload example: {"reason": "high_audio"}
            details = f"**Reason**: {payload.get('reason', 'unknown')}"
        elif event_type == "intervention_start":
            # Payload example: {"type": "breathing", "id": "box_breathing"}
            details = f"**Type**: {payload.get('type')}, **ID**: {payload.get('id', 'N/A')}"
        elif event_type == "user_feedback":
            # Payload example: {"intervention_type": "...", "feedback_value": "helpful"}
            details = f"**Rating**: {str(payload.get('feedback_value', '')).upper()} for {payload.get('intervention_type', 'unknown')}"
        elif event_type == "mode_change":
             details = f"{payload.get('old_mode', '?')} -> {payload.get('new_mode', '?')}"
        else:
            # Generic payload formatting
            details = str(payload)

        # Escape pipes to prevent breaking the markdown table
        details = details.replace("|", "\\|")
            elif etype == "LMM_SUGGESTION":
                 sug = event["details"].get("suggestion", {})
                 details_str = f"Proposed: {sug.get('id') or sug.get('type')}"

            else:
                details_str = str(event["details"])

            f.write(f"| {time_str} | {etype} | {details_str} |\n")

    print(f"Report generated at: {output_file}")

def main():
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

        markdown_content += f"| {time_str} | **{event_type}** | {details} |\n"


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
    # Ensure output dir exists
            # 5. Mode Changes

class TimelineGenerator:
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.events: List[Dict[str, Any]] = []

    def parse_log(self):
        """Parses the log file and extracts relevant events."""
        if not os.path.exists(self.log_file_path):
            print(f"Error: Log file not found at {self.log_file_path}")
            return

        with open(self.log_file_path, 'r') as f:
            for line in f:
                self._parse_line(line)

    def _parse_line(self, line: str):
        # Expected format: 2026-01-02T09:37:24.486527 [LEVEL] Message
        # Regex to capture timestamp, level, and message
        match = re.match(r'^([\d\-T:\.]+)\s+\[(\w+)\]\s+(.*)$', line.strip())
        if not match:
            return

        timestamp_str, level, message = match.groups()
        try:
            timestamp = datetime.datetime.fromisoformat(timestamp_str)
        except ValueError:
            return # Skip if timestamp format is invalid

        # Classify events based on message content
        event = {
            "timestamp": timestamp,
            "level": level,
            "raw_message": message,
            "type": "generic",
            "details": {}
        }

        if "Triggering LMM analysis" in message:
            event["type"] = "lmm_trigger"
            # Extract reason if possible
            reason_match = re.search(r'Reason: ([\w_]+)', message)
            if reason_match:
                event["details"]["reason"] = reason_match.group(1)

        elif "StateEngine: Updated state to" in message:
            event["type"] = "state_update"
            # Extract state dict
            try:
                state_str = message.split("Updated state to ", 1)[1]
                # Allow for simple eval of dict string (safe enough for local logs)
                # or better, json.loads if valid json (it uses single quotes in logs usually)
                import ast
                state_dict = ast.literal_eval(state_str)
                event["details"]["state"] = state_dict
            except Exception:
                pass

        elif "LMM suggested intervention:" in message:
            event["type"] = "intervention_suggestion"
            try:
                sugg_str = message.split("LMM suggested intervention: ", 1)[1]
                import ast
                sugg_dict = ast.literal_eval(sugg_str)
                event["details"]["suggestion"] = sugg_dict
            except Exception:
                pass

        elif "InterventionEngine: Starting" in message or "Intervention (" in message and ": Started" in message:
             event["type"] = "intervention_start"
             # Try to extract type/message
             # "Intervention (Type: box_breathing): Started."
             type_match = re.search(r'Type: ([\w_]+)', message)
             if type_match:
                 event["details"]["intervention_type"] = type_match.group(1)

        elif "Event: user_feedback" in message:
            event["type"] = "user_feedback"
            # Extract payload
            try:
                payload_str = message.split("| Payload: ", 1)[1]
                import ast
                payload = ast.literal_eval(payload_str)
                event["details"] = payload
            except Exception:
                pass

        elif "LogicEngine Notification: Mode changed" in message:
            event["type"] = "mode_change"
            # "Mode changed from active to snoozed"
            change_match = re.search(r'from (\w+) to (\w+)', message)
            if change_match:
                event["details"]["old_mode"] = change_match.group(1)
                event["details"]["new_mode"] = change_match.group(2)

        self.events.append(event)

    def generate_report(self, output_file: str):
        """Generates a Markdown timeline report."""
        if not self.events:
            print("No events found to report.")
            return

        # Sort events by timestamp
        self.events.sort(key=lambda x: x["timestamp"])

        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_file, 'w') as f:
            f.write("# ASDGPT Event Timeline\n\n")
            f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Source Log:** {self.log_file_path}\n\n")

            f.write("| Timestamp | Event Type | Details |\n")
            f.write("| --- | --- | --- |\n")

            for event in self.events:
                ts = event["timestamp"].strftime("%H:%M:%S.%f")[:-3]
                e_type = event["type"]
                details_str = ""

                if e_type == "lmm_trigger":
                    details_str = f"**Trigger:** {event['details'].get('reason', 'unknown')}"
                elif e_type == "state_update":
                    state = event["details"].get("state", {})
                    # Format state compactly: A:50 O:20 ...
                    state_compact = ", ".join([f"{k[0].upper()}:{v}" for k, v in state.items()])
                    details_str = f"**State Update:** {state_compact}"
                elif e_type == "intervention_suggestion":
                    sugg = event["details"].get("suggestion", {})
                    details_str = f"**Suggestion:** {sugg.get('type') or sugg.get('id')} - \"{sugg.get('message', '')[:30]}...\""
                elif e_type == "intervention_start":
                    details_str = f"**Intervention Started:** {event['details'].get('intervention_type', 'unknown')}"
                elif e_type == "user_feedback":
                    details_str = f"**Feedback:** {event['details'].get('feedback_value', 'unknown')} on {event['details'].get('intervention_type')}"
                elif e_type == "mode_change":
                    details_str = f"**Mode:** {event['details'].get('old_mode')} -> {event['details'].get('new_mode')}"
                else:
                    details_str = event["raw_message"]

                # Escape pipes in details for markdown table
                details_str = details_str.replace("|", "\\|")

                f.write(f"| {ts} | {e_type} | {details_str} |\n")

        print(f"Timeline report generated at: {output_file}")

if __name__ == "__main__":
    # Attempt to import config for defaults, but be robust if it fails
    default_log = "acr_app.log"
    try:
        import config
        if hasattr(config, 'LOG_FILE'):
            default_log = config.LOG_FILE
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Generate a timeline report from ASDGPT logs.")
    parser.add_argument("--log", type=str, default=default_log, help="Path to the log file.")
    parser.add_argument("--output", type=str, default="user_data/timeline_report.md", help="Path to the output markdown file.")

    args = parser.parse_args()

    generator = TimelineGenerator(args.log)
    generator.parse_log()
    generator.generate_report(args.output)
import json
import os
import argparse
import datetime

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
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate timeline report from ACR events.")
    parser.add_argument("--events", default=DEFAULT_EVENTS_FILE, help="Path to events.jsonl")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to output markdown file")

    args = parser.parse_args()

    events_list = parse_events(args.events)
    generate_markdown(events_list, args.output)
    print(f"Parsing log file: {args.log}")
    events = process_log_file(args.log)
    print(f"Found {len(events)} significant events.")

    generate_markdown_report(events, args.output)

if __name__ == "__main__":
    main()
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
    events = parse_events(args.events)
    generate_markdown(events, args.output)
