import datetime
import config
import os
import json
import logging
from logging.handlers import RotatingFileHandler

class DataLogger:
    def __init__(self, log_file_path=None, events_file_path=None):
        self.log_file_path = log_file_path or config.LOG_FILE
        self.events_file_path = events_file_path or getattr(config, 'EVENTS_FILE', 'user_data/events.jsonl')

        # Ensure log directory exists
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print(f"Error creating log directory {log_dir}: {e}. Logging to current directory.")
                self.log_file_path = os.path.basename(self.log_file_path)

        # Ensure events directory exists
        events_dir = os.path.dirname(self.events_file_path)
        if events_dir and not os.path.exists(events_dir):
             try:
                os.makedirs(events_dir)
             except OSError as e:
                print(f"Error creating events directory {events_dir}: {e}.")

        # Setup Python Logging with Rotation
        self.logger = logging.getLogger("ACR_DataLogger")
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
        self.logger.propagate = False # Prevent double logging if root logger is configured elsewhere

        # Check if handlers already exist to avoid duplication on re-init
        if not self.logger.handlers:
            # File Handler with Rotation (Max 5MB, keep 3 backups)
            try:
                file_handler = RotatingFileHandler(
                    self.log_file_path,
                    maxBytes=5*1024*1024,
                    backupCount=3,
                    encoding='utf-8'
                )
                formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f"CRITICAL: Failed to setup logging handler for {self.log_file_path}: {e}")

            # Console Handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        self.log_info(f"DataLogger initialized. Log level: {config.LOG_LEVEL}. Log file: {self.log_file_path}")

    def _get_timestamp(self):
        return datetime.datetime.now().isoformat()

    def log_info(self, message):
        self.logger.info(message)

    def log_warning(self, message):
        self.logger.warning(message)

    def log_error(self, message, details=""):
        full_message = f"{message} | Details: {details}" if details else message
        self.logger.error(full_message)

    def log_debug(self, message):
        self.logger.debug(message)

    def log_event(self, event_type, payload):
        """
        Logs a structured event to a JSONL file.
        Example: event_type="user_feedback", payload={"intervention_id": "xyz", "rating": "helpful"}
        """
        # Also log to main log for context (INFO level for visibility)
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info(f"Event: {event_type} | Payload: {payload}")

        # Write to events.jsonl (Manual append is fine for JSONL, maybe simple rotation later if needed)
        # For events, we want strict history, so usually we don't rotate/delete as aggressively as debug logs.
        # But to prevent infinite growth, we could apply rotation here too.
        # For now, keeping manual append as per original design but ensuring robust write.

        event_entry = {
            "timestamp": self._get_timestamp(),
            "event_type": event_type,
            "payload": payload
        }

        try:
            with open(self.events_file_path, "a") as f:
                f.write(json.dumps(event_entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write event to {self.events_file_path}: {e}")

if __name__ == '__main__':
    # Test DataLogger
    if not hasattr(config, 'LOG_FILE'): config.LOG_FILE = "test_app_log.txt"
    if not hasattr(config, 'LOG_LEVEL'): config.LOG_LEVEL = "DEBUG"
    if not hasattr(config, 'EVENTS_FILE'): config.EVENTS_FILE = "test_events.jsonl"

    logger = DataLogger()
    logger.log_info("This is an info message.")
    logger.log_warning("This is a warning message.")
    logger.log_error("This is an error message.", "Some additional details here.")
    logger.log_debug("This is a debug message.")

    logger.log_event("test_event", {"data": "sample_value", "id": 123})

    # Verify rotation doesn't crash
    # (We won't fill 5MB here, but just ensuring init works)
    print("Check log files.")
