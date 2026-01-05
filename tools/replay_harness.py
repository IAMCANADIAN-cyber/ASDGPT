import time
import json
import threading
import sys
import os
import queue
from typing import Optional, Dict, Any, List, Union
import logging

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import numpy as np
except ImportError:
    np = None

from core.logic_engine import LogicEngine
from core.data_logger import DataLogger
from core.lmm_interface import LMMInterface
from core.intervention_engine import InterventionEngine

# Mock LMM Interface for deterministic replay
class MockReplayLMMInterface(LMMInterface):
    def __init__(self, response_queue: queue.Queue):
        # Initialize without real credentials
        self.response_queue = response_queue
        self.logger = logging.getLogger("ReplayLMM")

    def process_data(self, video_data=None, audio_data=None, user_context=None) -> Optional[Dict]:
        try:
            # Return the next queued response
            if not self.response_queue.empty():
                response = self.response_queue.get_nowait()
                return response
            return None
        except queue.Empty:
            return None

    def get_intervention_suggestion(self, analysis: Dict) -> Optional[Dict]:
        return analysis.get("suggestion")

class ReplayHarness:
    def __init__(self, config_overrides_or_dataset: Optional[Union[Dict, str]] = None):
        self.events = []
        self.lmm_responses = queue.Queue()
        self.detected_interventions = []
        self.state_history = []
        self.dataset = []

        # Determine if we were passed a config dict or a dataset file path (legacy/test support)
        self.config_overrides = {}
        if isinstance(config_overrides_or_dataset, dict):
            self.config_overrides = config_overrides_or_dataset
        elif isinstance(config_overrides_or_dataset, str):
            # It's a file path
            try:
                with open(config_overrides_or_dataset, 'r') as f:
                    self.dataset = json.load(f)
            except Exception as e:
                print(f"Error loading dataset: {e}")

        # Setup Logic Engine
        self.logger = DataLogger(log_file_path="replay_log.txt")
        self.lmm_interface = MockReplayLMMInterface(self.lmm_responses)
        self.logic_engine = LogicEngine(
            logger=self.logger,
            lmm_interface=self.lmm_interface
        )

        # Override Intervention Engine to capture triggers instead of executing
        self.real_intervention_engine = InterventionEngine(self.logic_engine)
        self.logic_engine.set_intervention_engine(self.real_intervention_engine)

        # Hook into intervention start
        self.original_start_intervention = self.real_intervention_engine.start_intervention
        self.real_intervention_engine.start_intervention = self._mock_start_intervention

        # Configure Logic Engine for testing
        self.logic_engine.lmm_call_interval = 0.1 # Fast checks
        self.logic_engine.min_lmm_interval = 0
        self.logic_engine.audio_threshold_high = 0.5
        self.logic_engine.video_activity_threshold_high = 10.0

        # Apply overrides
        for k, v in self.config_overrides.items():
            setattr(self.logic_engine, k, v)

    def _mock_start_intervention(self, intervention_details: Dict[str, Any]) -> bool:
        self.detected_interventions.append(intervention_details)
        return True

    def add_lmm_response(self, response: Dict[str, Any]):
        """Queue a mock LMM response for the next trigger."""
        self.lmm_responses.put(response)

    def run_step(self, video_frame: Optional[Any] = None, audio_chunk: Optional[Any] = None):
        """
        Simulate one time step of the loop.
        """
        if video_frame is not None and np is not None:
             self.logic_engine.process_video_data(video_frame)

        if audio_chunk is not None and np is not None:
             self.logic_engine.process_audio_data(audio_chunk)

        self.logic_engine.update()

        # Wait for any background LMM thread to finish
        if self.logic_engine.lmm_thread and self.logic_engine.lmm_thread.is_alive():
            self.logic_engine.lmm_thread.join()

        # Capture state
        self.state_history.append(self.logic_engine.state_engine.get_state())

    def run(self) -> Dict[str, Any]:
        """
        Run through the loaded dataset (legacy support).
        """
        if not self.dataset:
            print("No dataset loaded.")
            return {}

        correct = 0
        false_positives = 0
        false_negatives = 0

        for event in self.dataset:
            # Clear previous state? Or keep continuous?
            # Usually replay tests want continuity or explicit reset.
            # Here we assume continuity or user handles it.

            # Setup inputs
            input_data = event.get("input", {})
            audio_level = input_data.get("audio_level", 0.0)

            # Synthesize data based on level
            # Just create a chunk with that RMS
            audio_chunk = None
            if np is not None:
                audio_chunk = np.ones(1024) * audio_level

            # LMM Mock Response
            expected = event.get("expected_outcome", {})
            expected_intervention = expected.get("intervention")

            # If expected intervention, we need to ensure LMM would suggest it if triggered
            # Or if it's a system trigger.
            # For this harness, if we want to test LogicEngine, we need to mock what LMM *would* say
            # or rely on system triggers.

            if expected_intervention == "noise_alert":
                 # This is likely a system trigger test, no LMM response needed if system handles it.
                 # LogicEngine uses system triggers for loud noise?
                 # Yes, but it triggers LMM first with reason "high_audio_level".
                 # The LMM response logic in LogicEngine then checks visual_context or suggestion.

                 # LogicEngine V2 (current):
                 # 1. Event triggers LMM call.
                 # 2. LMM returns.
                 # 3. If LMM returns suggestion OR reflexive trigger, intervention starts.

                 # So we need to queue an LMM response for this event to complete the loop.
                 self.add_lmm_response({
                     "state_estimation": {"arousal": 60},
                     "suggestion": {"id": expected_intervention}
                 })
            else:
                 # Default benign response
                 self.add_lmm_response({
                     "state_estimation": {"arousal": 50},
                     "suggestion": None
                 })

            self.detected_interventions = [] # Reset for this step
            self.run_step(audio_chunk=audio_chunk)

            # Verification
            triggered = None
            if self.detected_interventions:
                triggered = self.detected_interventions[0].get("id")

            if triggered == expected_intervention:
                correct += 1
            else:
                if triggered and not expected_intervention:
                    false_positives += 1
                elif expected_intervention and not triggered:
                    false_negatives += 1

        return {
            "total_events": len(self.dataset),
            "correct_triggers": correct,
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }

    def get_results(self):
        return {
            "interventions": self.detected_interventions,
            "state_history": self.state_history
        }

if __name__ == "__main__":
    # Simple self-test
    if np is None:
        print("Numpy not found, skipping harness test.")
        sys.exit(0)

    harness = ReplayHarness()

    # 1. Queue a response
    harness.add_lmm_response({
        "state_estimation": {"arousal": 80, "overload": 20},
        "suggestion": {"id": "box_breathing"}
    })

    # 2. Trigger with high audio
    audio = np.ones(1024) * 0.9
    harness.run_step(audio_chunk=audio)

    # 3. Check results
    results = harness.get_results()
    print("Detected Interventions:", results["interventions"])
    if results["interventions"] and results["interventions"][0]["id"] == "box_breathing":
        print("Harness Self-Test PASSED")
    else:
        print("Harness Self-Test FAILED")
