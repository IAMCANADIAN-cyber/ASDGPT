import sys
import os
import time
import logging
import argparse
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.lmm_interface import LMMInterface
import config

# Setup basic logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BenchmarkLogger:
    def log_info(self, msg): logging.info(msg)
    def log_warning(self, msg): logging.warning(msg)
    def log_error(self, msg, details=""): logging.error(f"{msg} | {details}")
    def log_debug(self, msg): logging.debug(msg)

def run_benchmark(mock=False):
    print("----------------------------------------------------------------")
    print("Running LMM Benchmark")
    print("----------------------------------------------------------------")

    logger = BenchmarkLogger()
    lmm = LMMInterface(data_logger=logger)

    print(f"Target URL: {lmm.llm_url}")
    print(f"Model ID: {config.LOCAL_LLM_MODEL_ID}")

    if mock:
        print("MOCK MODE ENABLED")
        lmm.check_connection = MagicMock(return_value=True)
        lmm.process_data = MagicMock(return_value={
            "state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50},
            "suggestion": None
        })

    # 1. Check Connection
    print("\n[1/3] Checking Connection...")
    start_time = time.time()
    connected = lmm.check_connection()
    duration = time.time() - start_time

    if connected:
        print(f"✅ Connection successful ({duration:.3f}s)")
    else:
        print(f"❌ Connection failed ({duration:.3f}s)")
        print("Skipping further tests. Please ensure your local LLM is running and accessible.")
        return

    # 2. Test Latency (Text Only)
    print("\n[2/3] Testing Text-Only Latency...")

    # Mock context
    user_context = {
        "current_mode": "benchmark",
        "sensor_metrics": {
            "audio_level": 0.5,
            "video_activity": 0.5
        }
    }

    start_time = time.time()
    response = lmm.process_data(user_context=user_context)
    duration = time.time() - start_time

    if response:
        print(f"✅ Response received in {duration:.3f}s")
        print(f"   State Estimation: {response.get('state_estimation')}")
        if duration > 2.0:
            print("   ⚠️ Latency is > 2s (Target: < 2s)")
    else:
        print(f"❌ Failed to get response ({duration:.3f}s)")

    # 3. Test Latency (With Dummy Image)
    # This is optional, but good to know if vision slows it down significantly.
    # We'll use a tiny 1x1 pixel base64 image.
    print("\n[3/3] Testing Vision Latency (1x1 px)...")
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="

    start_time = time.time()
    response = lmm.process_data(video_data=dummy_b64, user_context=user_context)
    duration = time.time() - start_time

    if response:
        print(f"✅ Response received in {duration:.3f}s")
    else:
        print(f"❌ Failed to get response ({duration:.3f}s)")

    print("\n----------------------------------------------------------------")
    print("Benchmark Complete")
    print("----------------------------------------------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LMM Benchmark")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without actual LMM connection")
    args = parser.parse_args()

    run_benchmark(mock=args.mock)
