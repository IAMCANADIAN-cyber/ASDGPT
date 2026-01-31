import logging
from logging.handlers import RotatingFileHandler
import config
import os
import json
import datetime
import sys

class DataLogger:
    def __init__(self, log_file_path=None, events_file_path=None):
        self.log_file_path = log_file_path or config.LOG_FILE
        self.events_file_path = events_file_path or getattr(config, 'EVENTS_FILE', 'user_data/events.jsonl')

        # Ensure directories exist
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print(f"Error creating log directory {log_dir}: {e}. Logging to current directory.")
                self.log_file_path = os.path.basename(self.log_file_path)

        events_dir = os.path.dirname(self.events_file_path)
        if events_dir and not os.path.exists(events_dir):
             try:
                os.makedirs(events_dir)
             except OSError as e:
                print(f"Error creating events directory {events_dir}: {e}.")

        # Configuration for Rotation
        self.max_bytes = getattr(config, 'LOG_MAX_BYTES', 5 * 1024 * 1024)
        self.backup_count = getattr(config, 'LOG_BACKUP_COUNT', 5)
        self.log_level_str = getattr(config, 'LOG_LEVEL', "INFO").upper()
        self.log_level = getattr(logging, self.log_level_str, logging.INFO)

        # --- App Logger Setup ---
        # Use a specific name to avoid conflict with root logger if used elsewhere
        self.app_logger = logging.getLogger("ACR_App")
        self.app_logger.setLevel(self.log_level)
        self.app_logger.propagate = False

        # Clear existing handlers to prevent duplication on re-init
        if self.app_logger.handlers:
            self.app_logger.handlers = []

        # Formatter
        # Matches previous style: timestamp [LEVEL] message
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S.%f')

        # File Handler (Rotating)
        try:
            file_handler = RotatingFileHandler(
                self.log_file_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            file_handler.setFormatter(formatter)
            self.app_logger.addHandler(file_handler)
        except Exception as e:
            print(f"CRITICAL: Failed to setup RotatingFileHandler for {self.log_file_path}: {e}")

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.app_logger.addHandler(console_handler)

        # --- Event Logger Setup ---
        self.event_logger = logging.getLogger("ACR_Events")
        self.event_logger.setLevel(logging.INFO)
        self.event_logger.propagate = False

        if self.event_logger.handlers:
            self.event_logger.handlers = []

        try:
            event_handler = RotatingFileHandler(
                self.events_file_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            # Raw formatter: just message (which will be JSON)
            event_formatter = logging.Formatter('%(message)s')
            event_handler.setFormatter(event_formatter)
            self.event_logger.addHandler(event_handler)
        except Exception as e:
            print(f"CRITICAL: Failed to setup RotatingFileHandler for events {self.events_file_path}: {e}")

        self.log_info(f"DataLogger initialized. Log level: {self.log_level_str}. Log file: {self.log_file_path}")

    def _get_timestamp(self):
        return datetime.datetime.now().isoformat()

    def log_info(self, message):
        self.app_logger.info(message)

    def log_warning(self, message):
        self.app_logger.warning(message)

    def log_error(self, message, details=""):
        full_message = f"{message} | Details: {details}" if details else message
        self.app_logger.error(full_message)

    def log_debug(self, message):
        self.app_logger.debug(message)

    def log_event(self, event_type, payload):
        """
        Logs a structured event to a JSONL file using rotation.
        """
        # Also log to main log for context (if level permits)
        if self.app_logger.isEnabledFor(logging.INFO):
             self.app_logger.info(f"Event: {event_type} | Payload: {payload}")

        # Construct event entry
        event_entry = {
            "timestamp": self._get_timestamp(),
            "event_type": event_type,
            "payload": payload
        }

        try:
            self.event_logger.info(json.dumps(event_entry))
        except Exception as e:
            self.app_logger.error(f"Failed to log event to jsonl: {e}")
