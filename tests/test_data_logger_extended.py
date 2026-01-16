import pytest
import os
import glob
import logging
import json
import shutil
from unittest.mock import patch, MagicMock
from core.data_logger import DataLogger
import config

class TestDataLoggerExtended:
    @pytest.fixture
    def temp_log_dir(self):
        # Create a temp directory for logs
        test_dir = "tests/temp_logs"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        os.makedirs(test_dir)
        yield test_dir
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_init_creates_directories(self, temp_log_dir):
        log_path = os.path.join(temp_log_dir, "subdir", "app.log")
        events_path = os.path.join(temp_log_dir, "subdir2", "events.jsonl")

        logger = DataLogger(log_file_path=log_path, events_file_path=events_path)

        assert os.path.exists(os.path.dirname(log_path))
        assert os.path.exists(os.path.dirname(events_path))

    def test_log_rotation(self, temp_log_dir):
        log_path = os.path.join(temp_log_dir, "rotated.log")
        events_path = os.path.join(temp_log_dir, "rotated_events.jsonl")

        # Override config temporarily
        # We need to ensure we are patching the attribute on the config module object that DataLogger sees.
        # Since DataLogger imports config, and we import config, they are the same module object in sys.modules.
        # But if LOG_MAX_BYTES doesn't exist in config.py, we must create it.
        # patch(..., create=True) handles this if we target the object directly,
        # but here we are targeting string path. 'config' is a module.

        with patch('core.data_logger.config.LOG_MAX_BYTES', 100, create=True), \
             patch('core.data_logger.config.LOG_BACKUP_COUNT', 2, create=True):

            logger = DataLogger(log_file_path=log_path, events_file_path=events_path)

            # Verify the patch worked
            assert logger.max_bytes == 100

            # Write enough data to trigger rotation
            # "Message X " * 5 is ~50 chars. Plus timestamp ~35 chars. Total ~85 bytes.
            # 10 messages = 850 bytes. Should produce multiple files if limit is 100.
            for i in range(20):
                logger.log_info(f"Message {i} " * 5)

            # Check if rotated files exist
            # Should have rotated.log, rotated.log.1, etc.
            files = glob.glob(f"{log_path}*")
            # Sort files to help debugging if assertion fails
            files.sort()
            print(f"Log files found: {files}")
            assert len(files) >= 2

            # Test event rotation
            for i in range(20):
                logger.log_event("test", {"data": "x" * 50})

            event_files = glob.glob(f"{events_path}*")
            event_files.sort()
            print(f"Event files found: {event_files}")
            assert len(event_files) >= 2

    def test_init_directory_creation_failure(self, temp_log_dir):
        # Simulate permission error when creating directory
        # We'll try to create a log file inside a file treated as a directory, or just mock os.makedirs

        log_path = os.path.join(temp_log_dir, "fail_dir", "app.log")

        with patch('os.makedirs', side_effect=OSError("Permission denied")):
            # It should fall back to current directory filename
            logger = DataLogger(log_file_path=log_path)

            # Check that it fell back (internal state)
            assert logger.log_file_path == "app.log"

            # Cleanup the fallback file if it was created
            if os.path.exists("app.log"):
                os.remove("app.log")

    def test_rotating_handler_setup_failure(self, temp_log_dir):
        log_path = os.path.join(temp_log_dir, "app.log")

        # Mock RotatingFileHandler to raise exception
        with patch('core.data_logger.RotatingFileHandler', side_effect=Exception("Disk full")):
            # Should not crash, but print error
            logger = DataLogger(log_file_path=log_path)

            # Check that app_logger has only stream handler (console)
            # (Note: implementation adds console handler after file handler attempt)
            assert len(logger.app_logger.handlers) == 1
            assert isinstance(logger.app_logger.handlers[0], logging.StreamHandler)

    def test_log_event_json_serialization_error(self, temp_log_dir):
        logger = DataLogger(log_file_path=os.path.join(temp_log_dir, "app.log"))

        # Create an object that is not JSON serializable
        class Unserializable:
            pass

        obj = Unserializable()

        # Should catch exception and log to error log
        # We need to spy on app_logger.error
        with patch.object(logger.app_logger, 'error') as mock_error:
            logger.log_event("bad_payload", {"data": obj})
            mock_error.assert_called_once()
            args, _ = mock_error.call_args
            assert "Failed to log event to jsonl" in args[0]

    def test_log_levels(self, temp_log_dir):
        log_path = os.path.join(temp_log_dir, "levels.log")
        logger = DataLogger(log_file_path=log_path)

        # We can mock the underlying logger to verify calls
        with patch.object(logger.app_logger, 'info') as mock_info, \
             patch.object(logger.app_logger, 'warning') as mock_warn, \
             patch.object(logger.app_logger, 'error') as mock_error, \
             patch.object(logger.app_logger, 'debug') as mock_debug:

            logger.log_info("info")
            mock_info.assert_called_with("info")

            logger.log_warning("warn")
            mock_warn.assert_called_with("warn")

            logger.log_error("err")
            mock_error.assert_called_with("err")

            logger.log_error("err", details="details")
            mock_error.assert_called_with("err | Details: details")

            logger.log_debug("dbg")
            mock_debug.assert_called_with("dbg")
