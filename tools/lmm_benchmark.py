import sys
import os
import time
import logging
import argparse
from unittest.mock import MagicMock
import json

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

def run_benchmark(use_mock=False):
def run_benchmark(mock=False):
    print("----------------------------------------------------------------")
    print(f"Running LMM Benchmark (Mock: {use_mock})")
    print("----------------------------------------------------------------")

    logger = BenchmarkLogger()
    lmm = LMMInterface(data_logger=logger)

    if use_mock:
        print("🛠️  Activating Mock Mode...")
        # Patch requests.get and requests.post on the lmm instance or globally
        import requests

        # Mock Response Object
        class MockResponse:
            def __init__(self, json_data, status_code=200):
                self._json_data = json_data
                self.status_code = status_code

            def json(self):
                return self._json_data

            def raise_for_status(self):
                if self.status_code != 200:
                    raise requests.exceptions.HTTPError(f"Mock Error {self.status_code}")

        def mock_get(url, timeout=None):
            # Simulate models endpoint
            return MockResponse({"data": [{"id": "mock-model"}]})

        def mock_post(url, json=None, timeout=None):
            import json as json_lib  # Alias to avoid conflict with the argument 'json'
            # Simulate latency
            time.sleep(0.5)

            # Simulate LMM response structure
            response_content = {
                "state_estimation": {
                    "arousal": 42,
                    "overload": 10,
                    "focus": 85,
                    "energy": 60,
                    "mood": 75
                },
                "suggestion": {
                    "id": "box_breathing",
                    "type": "physiology",
                    "message": "Breathe in..."
                }
            }

            # Wrap in OpenAI format
            full_response = {
                "choices": [{
                    "message": {
                        "content": f"```json\n{json_lib.dumps(response_content)}\n```"
                    }
                }]
            }
            return MockResponse(full_response)

        # Apply mocks
        lmm.check_connection = lambda: True # Force connection check true for speed
        requests.post = mock_post
        # requests.get is used in check_connection, but we overrode that method directly above.
        # But for completeness if we didn't override check_connection:
        requests.get = mock_get


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
    parser.add_argument("--mock", action="store_true", help="Run with mocked LMM responses")
    args = parser.parse_args()

    run_benchmark(use_mock=args.mock)
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without actual LMM connection")
    args = parser.parse_args()

    run_benchmark(mock=args.mock)
