import pytest
from unittest.mock import patch, MagicMock
import sys
import importlib

class TestWindowSensorSanitization:
    @pytest.fixture(autouse=True)
    def setup_modules(self):
        # Create a mock config
        self.mock_config = MagicMock()
        self.mock_config.SENSITIVE_APP_KEYWORDS = []

        # Patch sys.modules
        patcher = patch.dict(sys.modules, {'config': self.mock_config})
        patcher.start()

        # Reload window_sensor to use the mock config
        import sensors.window_sensor
        importlib.reload(sensors.window_sensor)

        yield

        patcher.stop()

    @pytest.fixture
    def sensor(self):
        from sensors.window_sensor import WindowSensor
        return WindowSensor()

    def test_sanitize_emails(self, sensor):
        assert sensor._sanitize_title("Hello user@example.com") == "Hello [EMAIL_REDACTED]"
        assert sensor._sanitize_title("Contact support@company.co.uk") == "Contact [EMAIL_REDACTED]"
        assert sensor._sanitize_title("invalid-email@com") == "invalid-email@com"

    def test_sanitize_paths(self, sensor):
        assert sensor._sanitize_title("Editing C:\\Users\\Name\\Doc.txt") == "Editing [PATH_REDACTED]"
        assert sensor._sanitize_title("Open /home/user/project/file.py") == "Open [PATH_REDACTED]"

    def test_sanitize_sensitive_apps(self, sensor):
        assert sensor._sanitize_title("KeePass - My Vault") == "[REDACTED_SENSITIVE_APP]"

        # Update the mock config directly
        self.mock_config.SENSITIVE_APP_KEYWORDS = ['secretapp']

        assert sensor._sanitize_title("Using SecretApp now") == "[REDACTED_SENSITIVE_APP]"

    def test_sanitize_combined(self, sensor):
        # Ensure default state
        self.mock_config.SENSITIVE_APP_KEYWORDS = []

        title = "Editing /home/user/secret.txt in 1Password"
        assert sensor._sanitize_title(title) == "[REDACTED_SENSITIVE_APP]"
