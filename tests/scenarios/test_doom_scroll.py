
import unittest
import numpy as np
import time
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
from core.logic_engine import LogicEngine
from core.state_engine import StateEngine

class TestDoomScrollScenario(unittest.TestCase):
    """
    Verifies that the system correctly identifies and intervenes on a "Doom Scrolling" scenario.
    This uses the ReplayHarness infrastructure but constructs a specific event sequence programmatically
    or validates against a specific subset of events.
    """

    def test_doom_scroll_trigger(self):
        # 1. Define the Scenario
        events = []
        for i in range(4):
            events.append({
                "id": f"phone_usage_{i}",
                "description": f"User looking at phone, frame {i}",
                "input": {
                    "audio_level": 0.1, # Quiet
                    "video_activity": 5.0 # Low movement
                },
                "expected_outcome": {
                    "intervention": "doom_scroll_breaker" if i >= 2 else None, # Trigger on 3rd (index 2) match?
                    "visual_context": ["phone_usage"]
                }
            })

        class CustomMockLMM:
            def __init__(self):
                self.current_visual_context = []
                self.last_analysis = {}

            def set_context(self, visual_context):
                self.current_visual_context = visual_context

            def process_data(self, video_data=None, audio_data=None, user_context=None):
                analysis = {
                    "state_estimation": {
                        "arousal": 50, "overload": 10, "focus": 50, "energy": 50, "mood": 50
                    },
                    "visual_context": self.current_visual_context,
                    "suggestion": None
                }
                self.last_analysis = analysis
                return analysis

            def get_intervention_suggestion(self, analysis):
                return analysis.get("suggestion")

        class MockInterventionEngine:
            def __init__(self):
                self.interventions_triggered = []

            def get_suppressed_intervention_types(self):
                return []

            def get_preferred_intervention_types(self):
                return []

            def start_intervention(self, suggestion):
                self.interventions_triggered.append(suggestion)

        # Initialize LogicEngine with our Custom Mock
        mock_lmm = CustomMockLMM()
        mock_ie = MockInterventionEngine()
        logger = LogicEngine(lmm_interface=mock_lmm).logger # Hack to get a logger or create new one

        class SyncLogicEngine(LogicEngine):
            def _trigger_lmm_analysis(self, reason="unknown", allow_intervention=True):
                # Bypass threading, call directly
                payload = self._prepare_lmm_data(trigger_reason=reason)
                if payload:
                    self._run_lmm_analysis_async(payload, allow_intervention)

        engine = SyncLogicEngine(logger=logger, lmm_interface=mock_lmm)
        engine.set_intervention_engine(mock_ie)
        engine.doom_scroll_trigger_threshold = 3 # Ensure default

        # Allow rapid triggers
        engine.min_lmm_interval = 0
        engine.lmm_call_interval = 0

        print("\n--- Starting Doom Scroll Scenario Test ---")

        # 3. Run the Scenario
        results = []
        for i, event in enumerate(events):
            print(f"Processing event {i}: {event['id']}")

            # Setup Mock
            visual_ctx = event['expected_outcome'].get("visual_context", [])
            mock_lmm.set_context(visual_ctx)
            mock_ie.interventions_triggered = []

            # Feed Data (to satisfy _prepare_lmm_data checks)
            engine.process_video_data(np.zeros((100, 100, 3), dtype=np.uint8))
            engine.process_audio_data(np.zeros(1024))

            # Trigger Update
            # Force time check to pass if needed, but we set intervals to 0.
            engine.last_lmm_call_time = 0
            engine.update()

            # Verify
            triggered = [inv['id'] for inv in mock_ie.interventions_triggered]
            expected = event['expected_outcome']['intervention']

            print(f"  Visual Context: {visual_ctx}")
            print(f"  Persistence Count: {engine.context_persistence.get('phone_usage', 0)}")
            print(f"  Triggered: {triggered}")

            if expected:
                if expected in triggered:
                    print("  [PASS] Triggered expected intervention.")
                    results.append(True)
                else:
                    print(f"  [FAIL] Expected {expected}, got {triggered}")
                    results.append(False)
            else:
                if not triggered:
                    print("  [PASS] No intervention triggered (correct).")
                    results.append(True)
                else:
                    print(f"  [FAIL] Expected None, got {triggered}")
                    results.append(False)

        # 4. Final Assertion
        self.assertTrue(all(results), "Doom Scroll scenario failed to trigger correctly.")

if __name__ == "__main__":
    unittest.main()
