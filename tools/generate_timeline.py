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

        markdown_content += f"| {time_str} | **{event_type}** | {details} |\n"

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
