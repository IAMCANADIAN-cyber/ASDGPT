import json
import random

def generate_events():
    events = []

    # Event Types
    scenarios = [
        ("stress_spike", 0.8, 0.1, {"arousal": "increase", "focus": "decrease"}, "noise_alert"),
        ("pacing", 0.1, 50.0, {"arousal": "increase", "energy": "increase"}, "movement_check"),
        ("silence", 0.05, 0.0, {"arousal": "decrease"}, None)
    ]

    # Generate 10 of each base scenario
    for i in range(10):
        for name, audio, video, state_change, intervention in scenarios:
            event_id = f"{name}_{i:02d}"

            # Add some noise to the inputs
            actual_audio = max(0.0, min(1.0, audio + random.uniform(-0.05, 0.05)))
            actual_video = max(0.0, video + random.uniform(-2.0, 2.0))

            # Duration varies slightly
            duration = random.randint(10, 60)

            event = {
                "id": event_id,
                "description": f"Synthetic {name} event",
                "duration_seconds": duration,
                "input": {
                    "audio_level": round(actual_audio, 3),
                    "video_activity": round(actual_video, 1)
                },
                "expected_outcome": {
                    "trigger_reason": "high_audio_level" if name == "stress_spike" else ("high_video_activity" if name == "pacing" else "periodic_check"),
                    "state_change": state_change,
                    "intervention": intervention
                }
            }
            events.append(event)

    # Add some "mixed" or "edge" cases
    mixed_cases = [
        {
            "id": "mixed_high_activity_noise",
            "description": "Loud noise and high activity",
            "duration_seconds": 15,
            "input": {"audio_level": 0.9, "video_activity": 60.0},
            "expected_outcome": {
                "trigger_reason": "high_audio_level", # Audio checked first in LogicEngine
                "state_change": {"arousal": "increase", "overload": "increase"},
                "intervention": "overstimulation_alert"
            }
        },
        {
            "id": "near_threshold_silence",
            "description": "Just below threshold silence",
            "duration_seconds": 30,
            "input": {"audio_level": 0.45, "video_activity": 18.0}, # Thresholds are 0.5 and 20.0
            "expected_outcome": {
                "trigger_reason": "periodic_check",
                "state_change": {"arousal": "stable"},
                "intervention": None
            }
        }
    ]

    events.extend(mixed_cases)

    return events

if __name__ == "__main__":
    dataset = generate_events()
    with open("datasets/synthetic_events.json", "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"Generated {len(dataset)} events in datasets/synthetic_events.json")
