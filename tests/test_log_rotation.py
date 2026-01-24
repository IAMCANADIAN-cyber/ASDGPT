import unittest
import os
import glob
import time
import json
import logging
from core.data_logger import DataLogger
import config
from unittest.mock import patch

class TestLogRotation(unittest.TestCase):
    def setUp(self):
        self.test_log_file = "test_rotation.log"
        self.test_events_file = "test_rotation_events.jsonl"

        # Cleanup previous test files
        self._cleanup()

        # Start patches
        self.max_bytes_patch = patch('core.data_logger.config.LOG_MAX_BYTES', 1000)
        self.backup_count_patch = patch('core.data_logger.config.LOG_BACKUP_COUNT', 3)
        self.log_level_patch = patch('core.data_logger.config.LOG_LEVEL', "DEBUG")

        self.max_bytes_patch.start()
        self.backup_count_patch.start()
        self.log_level_patch.start()

    def tearDown(self):
        # Stop patches
        self.max_bytes_patch.stop()
        self.backup_count_patch.stop()
        self.log_level_patch.stop()

        # Close handlers explicitly to release file locks (important on Windows, good practice generally)
        if hasattr(self, 'logger'):
            for handler in self.logger.app_logger.handlers:
                handler.close()
            for handler in self.logger.event_logger.handlers:
                handler.close()

        self._cleanup()

    def _cleanup(self):
        for f in glob.glob("test_rotation*"):
            try:
                os.remove(f)
            except OSError:
                pass

    def test_app_log_rotation(self):
        print("\n--- Testing App Log Rotation ---")
        self.logger = DataLogger(log_file_path=self.test_log_file, events_file_path=self.test_events_file)

        # Generate enough logs to rotate
        # Each line is approx 80-100 bytes. 1000 bytes limit -> ~10-15 lines.
        msg = "X" * 50 # 50 chars payload

        for i in range(50):
            self.logger.log_info(f"Msg {i}: {msg}")

        # Check if files exist
        files = glob.glob(f"{self.test_log_file}*")
        print(f"Log files found: {files}")

        # Should have at least the main file and .1
        self.assertTrue(os.path.exists(self.test_log_file), "Main log file missing")
        self.assertTrue(os.path.exists(f"{self.test_log_file}.1"), "Rotated log file .1 missing")

        # Verify content limit respected (roughly)
        size = os.path.getsize(f"{self.test_log_file}.1")
        self.assertTrue(size <= config.LOG_MAX_BYTES + 200, f"Rotated file size {size} too large")

    def test_events_log_rotation(self):
        print("\n--- Testing Events Log Rotation ---")
        self.logger = DataLogger(log_file_path=self.test_log_file, events_file_path=self.test_events_file)

        payload = {"data": "Y" * 50} # JSON overhead + timestamp + 50 chars

        for i in range(50):
            self.logger.log_event("test_event", payload)

        files = glob.glob(f"{self.test_events_file}*")
        print(f"Event files found: {files}")

        self.assertTrue(os.path.exists(self.test_events_file), "Main events file missing")
        self.assertTrue(os.path.exists(f"{self.test_events_file}.1"), "Rotated events file .1 missing")

        # Verify JSON validity of the main file
        with open(self.test_events_file, 'r') as f:
            lines = f.readlines()
            if lines:
                try:
                    json.loads(lines[-1])
                except json.JSONDecodeError:
                    self.fail("Last line of events file is not valid JSON")

if __name__ == '__main__':
    unittest.main()
