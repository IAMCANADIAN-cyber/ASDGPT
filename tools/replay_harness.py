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

class SynchronousLogicEngine(LogicEngine):
    """
    A subclass of LogicEngine that runs LMM analysis synchronously for testing.
    """
    def _trigger_lmm_analysis(self, reason: str = "unknown", allow_intervention: bool = True) -> None:
        if not self.lmm_interface:
            return

        lmm_payload = self._prepare_lmm_data(trigger_reason=reason)
        if not lmm_payload:
            return

        # Directly call the async worker method synchronously
        self._run_lmm_analysis_async(lmm_payload, allow_intervention)

class ReplayHarness:
    def __init__(self, dataset_path):
        self.dataset_path = dataset_path
        self.events = self._load_events()
        self.logger = DataLogger(log_file_path="replay_log.txt")
        self.mock_lmm = MockLMMInterface()
        self.mock_intervention = MockInterventionEngine()

        # Initialize LogicEngine with mocks using the synchronous subclass
        self.logic_engine = SynchronousLogicEngine(logger=self.logger, lmm_interface=self.mock_lmm)
        self.logic_engine.set_intervention_engine(self.mock_intervention)

        # Adjust settings for faster replay
        self.logic_engine.min_lmm_interval = 0 # Allow immediate triggers
        self.logic_engine.lmm_call_interval = 2 # Short interval

        # Override thresholds to match dataset generation assumptions
        # Assuming dataset uses values > 0.5 for high audio and > 20 for high video
        self.logic_engine.audio_threshold_high = 0.5
        self.logic_engine.video_activity_threshold_high = 20.0

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

            # Reset LogicEngine state slightly to ensure clean slate for event
            self.logic_engine.last_lmm_call_time = 0 # Force eligible for periodic check if needed

            # 2. Inject Sensor Data
            target_audio = event['input']['audio_level']
            audio_chunk = np.full(1024, target_audio)

            target_video = event['input']['video_activity']
            pixel_val = min(255, int(target_video))

            frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
            frame2 = np.full((100, 100, 3), pixel_val, dtype=np.uint8)

            # Inject
            self.logic_engine.process_video_data(frame1) # Set previous
            self.logic_engine.process_video_data(frame2) # Set current -> triggers diff calc
            self.logic_engine.process_audio_data(audio_chunk)

            # 3. Trigger LogicEngine Update
            # Force time to allow trigger
            self.logic_engine.last_lmm_call_time = time.time() - 100

            self.logic_engine.update()

            # 4. Verify Outcomes
            expected_intervention = event['expected_outcome'].get("intervention")
            actual_interventions = self.mock_intervention.interventions_triggered

            if expected_intervention:
                # Check if ANY of the triggered interventions match the type OR id
                match = next((i for i in actual_interventions if i.get('type') == expected_intervention or i.get('id') == expected_intervention), None)
                if match:
                    print(f"  [SUCCESS] Triggered expected intervention: {expected_intervention}")
                    results["correct_triggers"] += 1
                    results["triggered_interventions"] += 1
                else:
                    if len(actual_interventions) > 0:
                        got_types = [i.get('type', i.get('id')) for i in actual_interventions]
                        print(f"  [FAILURE] Expected {expected_intervention}, got {got_types}")
                        results["false_positives"] += 1 # Wrong one triggered
                    else:
                        print(f"  [FAILURE] Expected {expected_intervention}, got NONE")
                        results["false_negatives"] += 1
            else:
                if len(actual_interventions) == 0:
                     print(f"  [SUCCESS] Correctly triggered NO intervention.")
                     results["correct_triggers"] += 1
                else:
                    got_types = [i.get('type', i.get('id')) for i in actual_interventions]
                    print(f"  [FAILURE] Expected NONE, got {got_types}")
                    results["false_positives"] += 1
                    results["triggered_interventions"] += 1

        results["duration"] = time.time() - results["start_time"]
        results["intervention_rate_per_hour_simulated"] = (results["triggered_interventions"] / len(self.events)) * (3600 / 30) # Approx

        return results

    def print_report(self, results):
        print("\n" + "="*40)
        print("REPLAY HARNESS REPORT")
        print("="*40)
        print(f"Total Events: {results['total_events']}")
        print(f"Successful Matches: {results['correct_triggers']}")
        print(f"False Positives: {results['false_positives']}")
        print(f"False Negatives: {results['false_negatives']}")
        print("-" * 20)
        percentage = (results['correct_triggers'] / results['total_events']) * 100 if results['total_events'] > 0 else 0
        print(f"Accuracy: {percentage:.2f}%")
        print("="*40)

if __name__ == "__main__":
    harness = ReplayHarness("datasets/synthetic_events.json")
    results = harness.run()
    harness.print_report(results)
