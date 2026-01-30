import json
import time
import os
from typing import Dict, Any, Optional

class BiometricSensor:
    """
    Reads biometric data from a local file synced from the companion app.
    Default path: biometrics/current_metrics.json
    """

    def __init__(self, data_path: str = "biometrics/current_metrics.json", data_logger=None):
        self.data_path = data_path
        self.logger = data_logger
        self.last_read_time = 0
        self.cached_metrics = {}
        self._ensure_directory()

    def _ensure_directory(self):
        try:
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"BiometricSensor: Failed to create directory: {e}")

    def get_latest_metrics(self) -> Dict[str, Any]:
        """
        Reads the JSON file and returns the metrics.
        Returns empty dict if file not found or invalid.
        """
        if not os.path.exists(self.data_path):
            return {}

        try:
            # Check modification time to avoid re-reading unchanged file too often?
            # For now, just read.
            with open(self.data_path, 'r') as f:
                data = json.load(f)

            # Validate basic structure?
            # Expected: {"heart_rate": int, "steps": int, "sleep_score": int, "timestamp": float}
            self.cached_metrics = data
            return data
        except json.JSONDecodeError:
            if self.logger:
                self.logger.log_warning("BiometricSensor: Invalid JSON in metrics file.")
            return self.cached_metrics # Return last known good
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"BiometricSensor: Error reading metrics: {e}")
            return {}

if __name__ == '__main__':
    # Test
    test_path = "biometrics/test_metrics.json"
    sensor = BiometricSensor(data_path=test_path)

    # Write dummy data
    with open(test_path, 'w') as f:
        json.dump({"heart_rate": 75, "steps": 500, "timestamp": time.time()}, f)

    metrics = sensor.get_latest_metrics()
    print(f"Read metrics: {metrics}")
    assert metrics["heart_rate"] == 75

    # Clean up
    if os.path.exists(test_path):
        os.remove(test_path)
    print("BiometricSensor test passed.")
