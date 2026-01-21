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
    events.sort(key=lambda x: x.get('timestamp', ''))

    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ACR Timeline Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Time | Event Type | Details |\n")
        f.write("|---|---|---|\n")

        for event in events:
            ts_str = event.get('timestamp', 'Unknown')
            # Try to format timestamp if ISO
            try:
                dt = datetime.fromisoformat(ts_str)
                time_str = dt.strftime("%H:%M:%S")
            except ValueError:
                time_str = ts_str

            etype = event.get("event_type", "UNKNOWN")
            payload = event.get("payload", {})

            # Format details based on type
            details_str = ""
            if etype == "lmm_trigger":
                details_str = f"LMM Triggered: {payload.get('reason', 'unknown')}"
            elif etype == "state_update":
                s = payload
                details_str = f"Arousal:{s.get('arousal')} Overload:{s.get('overload')} Focus:{s.get('focus')}"
            elif etype == "intervention_start":
                details_str = f"**{payload.get('type')}** ({payload.get('id')})"
            elif etype == "user_feedback":
                details_str = f"**Rating**: {str(payload.get('feedback_value', '')).upper()} for {payload.get('intervention_type')}"
            else:
                details_str = str(payload)

            # Escape pipes
            details_str = details_str.replace("|", "\\|")

            f.write(f"| {time_str} | {etype} | {details_str} |\n")

    print(f"Report generated at: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate timeline report from ACR events.")
    parser.add_argument("--events", default=DEFAULT_EVENTS_FILE, help="Path to events.jsonl")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to output markdown file")

    args = parser.parse_args()

    events_list = parse_events(args.events)
    generate_markdown(events_list, args.output)
