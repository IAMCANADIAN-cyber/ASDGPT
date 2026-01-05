import time
import threading
import sys
import os
import unittest.mock as mock
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface

# Mocking LMM to simulate a slow network call
class SlowLMM(LMMInterface):
    def analyze_situation(self, audio_metrics, video_metrics, user_context):
        print("SlowLMM: Starting analysis (sleeping 3s)...")
        time.sleep(3)
        print("SlowLMM: Analysis complete.")
        return {
            "state_estimation": {"arousal": 50, "overload": 50, "focus": 50, "energy": 50, "mood": 50},
            "visual_context": [],
            "suggestion": None
        }

def verify_shutdown():
    print("--- Starting Shutdown Verification ---")

    # patch LMMInterface in logic engine
    with mock.patch('core.logic_engine.LMMInterface', side_effect=SlowLMM):
        engine = LogicEngine()

        # Start the engine
        engine.start()
        print("Engine started.")

        # Manually trigger LMM analysis (simulate threshold trigger)
        print("Triggering LMM analysis...")
        engine._trigger_lmm_analysis("test_trigger")

        # Give it a moment to start the thread
        time.sleep(0.5)

        if engine.lmm_thread and engine.lmm_thread.is_alive():
            print("LMM thread is running (as expected).")
        else:
            print("Error: LMM thread not running!")

        # Now Shutdown
        print("Initiating shutdown...")
        start_time = time.time()
        try:
            engine.shutdown()
        except AttributeError as e:
            print(f"Caught expected bug during shutdown: {e}")

        duration = time.time() - start_time
        print(f"Shutdown returned in {duration:.2f} seconds.")

        # Check if LMM thread is still alive
        if engine.lmm_thread and engine.lmm_thread.is_alive():
            print("FAILURE: LMM thread is still running after shutdown! (Zombie Thread)")
        else:
            print("SUCCESS: LMM thread was joined.")

        # Check if monitor thread is alive
        if engine.monitor_thread and engine.monitor_thread.is_alive():
             print("FAILURE: Monitor thread is still running!")
        else:
             print("SUCCESS: Monitor thread joined.")

if __name__ == "__main__":
    verify_shutdown()
