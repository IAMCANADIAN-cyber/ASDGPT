import sys
import os
import time
import logging
import argparse
import statistics
import json
import requests
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

def setup_mock_lmm(lmm_interface):
    """Mocks the network calls for the LMM interface for testing the benchmark script."""
    print("⚠️  RUNNING IN MOCK MODE (No actual network calls) ⚠️")

    def mock_post(*args, **kwargs):
        time.sleep(0.5) # Simulate network delay
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "state_estimation": {
                            "arousal": 50, "overload": 10, "focus": 80,
                            "energy": 70, "mood": 60
                        },
                        "suggestion": None
                    })
                }
            }]
        }
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    requests.post = mock_post

    # Mock check_connection specifically
    original_get = requests.get
    def mock_get(*args, **kwargs):
        if "models" in args[0]:
             mock_resp = MagicMock()
             mock_resp.status_code = 200
             return mock_resp
        return original_get(*args, **kwargs)
    requests.get = mock_get


def run_benchmark(iterations=5, use_vision=True, mock=False):
    print("----------------------------------------------------------------")
    print(f"Running LMM Benchmark (Iterations: {iterations}, Mock: {mock})")
    print("----------------------------------------------------------------")

    logger = BenchmarkLogger()
    lmm = LMMInterface(data_logger=logger)

    if mock:
        setup_mock_lmm(lmm)

    print(f"Target URL: {lmm.llm_url}")
    print(f"Model ID: {config.LOCAL_LLM_MODEL_ID}")

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

    # 2. Test Loop
    latencies = []
    successes = 0
    failures = 0

    print(f"\n[2/3] Running {iterations} iterations...")

    user_context = {
        "current_mode": "benchmark",
        "sensor_metrics": {
            "audio_level": 0.5,
            "video_activity": 0.5
        }
    }
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" if use_vision else None

    for i in range(iterations):
        sys.stdout.write(f"\rIteration {i+1}/{iterations}...")
        sys.stdout.flush()

        t_start = time.time()
        response = lmm.process_data(video_data=dummy_b64, user_context=user_context)
        t_end = time.time()

        if response:
            latencies.append(t_end - t_start)
            successes += 1
        else:
            failures += 1

        # Optional short sleep to be nice to local GPU?
        # time.sleep(0.1)

    print("\n") # Newline

    # 3. Report
    print("\n[3/3] Results")
    if latencies:
        avg_lat = statistics.mean(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        p95 = statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 20 else max_lat

        print(f"✅ Success Rate: {successes}/{iterations} ({successes/iterations*100:.1f}%)")
        print(f"⏱️  Average Latency: {avg_lat:.3f}s")
        print(f"    Min: {min_lat:.3f}s | Max: {max_lat:.3f}s | P95: {p95:.3f}s")

        if avg_lat > 2.0:
            print("⚠️  Performance Warning: Average latency > 2s")
    else:
        print("❌ All iterations failed.")

    print("\n----------------------------------------------------------------")
    print("Benchmark Complete")
    print("----------------------------------------------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASDGPT LMM Benchmark Tool")
    parser.add_argument("-n", "--iterations", type=int, default=5, help="Number of requests to run")
    parser.add_argument("--no-vision", action="store_true", help="Disable vision (send text only)")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no network)")

    args = parser.parse_args()

    run_benchmark(iterations=args.iterations, use_vision=not args.no_vision, mock=args.mock)
