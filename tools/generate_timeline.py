import json
import os
import argparse
from datetime import datetime

def parse_events(events_file):
    events = []
    if not os.path.exists(events_file):
        return []

    with open(events_file, 'r') as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events

def generate_markdown(events, output_file):
    if not events:
        print("No events found.")
        return

    # Sort events by timestamp
    events.sort(key=lambda x: x['timestamp'])

    markdown_content = "# ACR Timeline Report\n\n"
    markdown_content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    current_date = ""

    for event in events:
        ts = datetime.fromisoformat(event['timestamp'])
        date_str = ts.strftime('%Y-%m-%d')
        time_str = ts.strftime('%H:%M:%S')

        if date_str != current_date:
            markdown_content += f"## {date_str}\n\n"
            markdown_content += "| Time | Event Type | Details |\n"
            markdown_content += "| --- | --- | --- |\n"
            current_date = date_str

        event_type = event['event_type']
        payload = event['payload']

        # Format payload for readability
        details = ""
        if event_type == "state_update":
            details = ", ".join([f"{k}: {v}" for k, v in payload.items()])
        elif event_type == "lmm_trigger":
            details = f"Reason: {payload.get('reason', 'unknown')}"
        elif event_type == "intervention_start":
            details = f"Type: {payload.get('type')}, ID: {payload.get('id', 'N/A')}"
        elif event_type == "user_feedback":
            details = f"Rating: **{payload.get('feedback_value', '').upper()}** for {payload.get('intervention_type', 'unknown')}"
        else:
            details = str(payload)

        markdown_content += f"| {time_str} | **{event_type}** | {details} |\n"

    with open(output_file, 'w') as f:
        f.write(markdown_content)

    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate timeline report from ACR events.")
    parser.add_argument("--events", default="user_data/events.jsonl", help="Path to events.jsonl")
    parser.add_argument("--output", default="user_data/timeline_report.md", help="Path to output markdown file")

    args = parser.parse_args()

    events = parse_events(args.events)
    generate_markdown(events, args.output)
