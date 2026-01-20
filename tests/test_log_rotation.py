import unittest
import os
import glob
import time
import json
import logging
from unittest.mock import patch, MagicMock
from core.data_logger import DataLogger
import config

class TestLogRotation(unittest.TestCase):
    def setUp(self):
        self.test_log_file = "test_rotation.log"
        self.test_events_file = "test_rotation_events.jsonl"
        self._cleanup()

    def tearDown(self):
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

        # Patch config used by DataLogger
        with patch('core.data_logger.config.LOG_MAX_BYTES', 1000), \
             patch('core.data_logger.config.LOG_BACKUP_COUNT', 3), \
             patch('core.data_logger.config.LOG_LEVEL', "DEBUG"):

            self.logger = DataLogger(log_file_path=self.test_log_file, events_file_path=self.test_events_file)

            # Generate enough logs to rotate
            msg = "X" * 50
            for i in range(50):
                self.logger.log_info(f"Msg {i}: {msg}")

            files = glob.glob(f"{self.test_log_file}*")
            print(f"Log files found: {files}")

            self.assertTrue(os.path.exists(self.test_log_file), "Main log file missing")
            self.assertTrue(os.path.exists(f"{self.test_log_file}.1"), "Rotated log file .1 missing")

            size = os.path.getsize(f"{self.test_log_file}.1")
            self.assertTrue(size <= 1200, f"Rotated file size {size} too large")

    def test_events_log_rotation(self):
        print("\n--- Testing Events Log Rotation ---")

        with patch('core.data_logger.config.LOG_MAX_BYTES', 1000), \
             patch('core.data_logger.config.LOG_BACKUP_COUNT', 3):

            self.logger = DataLogger(log_file_path=self.test_log_file, events_file_path=self.test_events_file)

            payload = {"data": "Y" * 50}

            for i in range(50):
                self.logger.log_event("test_event", payload)

            files = glob.glob(f"{self.test_events_file}*")
            print(f"Event files found: {files}")

            self.assertTrue(os.path.exists(self.test_events_file), "Main events file missing")
            self.assertTrue(os.path.exists(f"{self.test_events_file}.1"), "Rotated events file .1 missing")

if __name__ == '__main__':
    unittest.main()
