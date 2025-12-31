import json
import time
import sys
import os
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.logic_engine import LogicEngine
from core.state_engine import StateEngine
from core.data_logger import DataLogger
import config

class MockLMMInterface:
    def __init__(self):
        self.last_analysis = {}
        self.current_expected_outcome = None

    def set_expectation(self, expected_outcome):
        self.current_expected_outcome = expected_outcome

    def process_data(self, video_data=None, audio_data=None, user_context=None):
        # Simulate LMM processing based on the expected outcome of the current event
        trigger_reason = user_context.get("trigger_reason")

        # Default analysis
        analysis = {
            "state_estimation": {
                "arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50
            },
            "suggestion": None
        }

        if self.current_expected_outcome:
            # Apply expected state changes
            if "state_change" in self.current_expected_outcome:
                changes = self.current_expected_outcome["state_change"]
                # Start from baseline
                est = analysis["state_estimation"]
                for dim, change in changes.items():
                    if change == "increase":
                        est[dim] = 80
                    elif change == "decrease":
                        est[dim] = 20
                    elif change == "stable":
                        est[dim] = 50

            # Apply intervention suggestion
            if self.current_expected_outcome.get("intervention"):
                analysis["suggestion"] = {
                    "type": self.current_expected_outcome["intervention"],
                    "message": "Simulated intervention message."
                }

        self.last_analysis = analysis
        return analysis

    def get_intervention_suggestion(self, analysis):
        return analysis.get("suggestion")

class MockInterventionEngine:
    def __init__(self):
        self.interventions_triggered = []

    def start_intervention(self, suggestion):
        self.interventions_triggered.append(suggestion)

class ReplayHarness:
    def __init__(self, dataset_path):
        self.dataset_path = dataset_path
        self.events = self._load_events()
        self.logger = DataLogger(log_file_path="replay_log.txt")
        self.mock_lmm = MockLMMInterface()
        self.mock_intervention = MockInterventionEngine()

        # Initialize LogicEngine with mocks
        self.logic_engine = LogicEngine(logger=self.logger, lmm_interface=self.mock_lmm)
        self.logic_engine.set_intervention_engine(self.mock_intervention)

        # Adjust settings for faster replay
        self.logic_engine.min_lmm_interval = 0 # Allow immediate triggers

    def _load_events(self):
        with open(self.dataset_path, 'r') as f:
            return json.load(f)

    def run(self):
        print(f"Starting replay of {len(self.events)} events...")

        results = {
            "total_events": len(self.events),
            "triggered_interventions": 0,
            "correct_triggers": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "start_time": time.time(),
        }

        for event in self.events:
            print(f"Processing event: {event['id']} ({event['description']})")

            # 1. Setup the mocks
            self.mock_lmm.set_expectation(event['expected_outcome'])
            self.mock_intervention.interventions_triggered = []

            # 2. Inject Sensor Data
            # LogicEngine calculates:
            # Audio: RMS
            # Video: Mean(AbsDiff(Frame1, Frame2))

            # To get specific Audio RMS 'L':
            # Create array of value 'L'. Sqrt(Mean(L^2)) = L.
            target_audio = event['input']['audio_level']
            audio_chunk = np.full(1024, target_audio)

            # To get specific Video Activity 'A':
            # Frame 1: All 0s
            # Frame 2: All 'A's
            # Diff = A. Mean = A.
            target_video = event['input']['video_activity']
            # Ensure target_video is within uint8 range (0-255) for this simplistic generation
            # If it's larger (unlikely for "mean diff"), we'd need a different strategy, but max here is usually < 255.
            pixel_val = min(255, int(target_video))

            frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
            frame2 = np.full((100, 100, 3), pixel_val, dtype=np.uint8)

            # Inject
            self.logic_engine.process_video_data(frame1) # Set previous
            self.logic_engine.process_video_data(frame2) # Set current -> triggers diff calc
            self.logic_engine.process_audio_data(audio_chunk)

            # 3. Trigger LogicEngine Update
            # We need to reset the timer to ensure it *can* trigger if conditions met
            # But we also want to respect the "trigger_reason" logic.
            # If input > threshold, it triggers.

            # Force time to allow trigger
            self.logic_engine.last_lmm_call_time = time.time() - 100

            self.logic_engine.update()

            # 4. Verify Outcomes
            expected_intervention = event['expected_outcome'].get("intervention")
            actual_interventions = self.mock_intervention.interventions_triggered

            if expected_intervention:
                if any(i['type'] == expected_intervention for i in actual_interventions):
                    print(f"  [SUCCESS] Triggered expected intervention: {expected_intervention}")
                    results["correct_triggers"] += 1
                    results["triggered_interventions"] += 1
                else:
                    if len(actual_interventions) > 0:
                        print(f"  [FAILURE] Expected {expected_intervention}, got {[i['type'] for i in actual_interventions]}")
                        results["false_positives"] += 1 # Wrong one triggered
                    else:
                        print(f"  [FAILURE] Expected {expected_intervention}, got NONE")
                        results["false_negatives"] += 1
            else:
                if len(actual_interventions) == 0:
                     print(f"  [SUCCESS] Correctly triggered NO intervention.")
                     results["correct_triggers"] += 1
                else:
                    print(f"  [FAILURE] Expected NONE, got {[i['type'] for i in actual_interventions]}")
                    results["false_positives"] += 1
                    results["triggered_interventions"] += 1

        results["duration"] = time.time() - results["start_time"]
        results["intervention_rate_per_hour_simulated"] = (results["triggered_interventions"] / len(self.events)) * (3600 / 30) # Approx

        self._print_report(results)

    def _print_report(self, results):
        print("\n" + "="*40)
        print("REPLAY HARNESS REPORT")
        print("="*40)
        print(f"Total Events: {results['total_events']}")
        print(f"Successful Matches: {results['correct_triggers']}")
        print(f"False Positives: {results['false_positives']}")
        print(f"False Negatives: {results['false_negatives']}")
        print("-" * 20)
        print(f"Accuracy: {(results['correct_triggers'] / results['total_events']) * 100:.2f}%")
        print("="*40)

if __name__ == "__main__":
    harness = ReplayHarness("datasets/synthetic_events.json")
    harness.run()
