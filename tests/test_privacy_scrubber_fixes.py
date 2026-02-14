import pytest
from unittest.mock import MagicMock, patch
import config
from sensors.window_sensor import WindowSensor

def test_config_sensitive_app_keywords_no_concatenation():
    """Verify that SENSITIVE_APP_KEYWORDS does not contain concatenated strings due to missing commas."""
    keywords = config.SENSITIVE_APP_KEYWORDS

    # Check for known concatenation artifacts from the bug
    assert "Credit CardPassword" not in keywords
    assert "SettingBank" not in keywords

    # Check for presence of split keywords
    assert "Credit Card" in keywords
    assert "Password" in keywords
    assert "Setting" in keywords
    assert "Bank" in keywords

@pytest.fixture
def mock_window_sensor():
    with patch('platform.system', return_value='Linux'), \
         patch('shutil.which', return_value='/usr/bin/xprop'):
        sensor = WindowSensor()
        # Explicitly set xprop_available to True as logic depends on it
        sensor.xprop_available = True
        return sensor

def test_window_sensor_linux_net_wm_name_priority(mock_window_sensor):
    """Verify that _get_active_window_linux prioritizes _NET_WM_NAME."""
    with patch('subprocess.run') as mock_run:
        # Mock finding the window ID
        mock_run.side_effect = [
            # 1. xprop -root _NET_ACTIVE_WINDOW -> 0x12345
            MagicMock(returncode=0, stdout="_NET_ACTIVE_WINDOW(WINDOW): window id # 0x12345\n"),
            # 2. xprop -id 0x12345 _NET_WM_NAME -> "UTF-8 Title"
            MagicMock(returncode=0, stdout='_NET_WM_NAME(UTF8_STRING) = "My UTF-8 Window 🚀"\n')
        ]

        title = mock_window_sensor.get_active_window()
        assert title == "My UTF-8 Window 🚀"

        # Verify calls
        assert mock_run.call_count == 2
        args, _ = mock_run.call_args_list[1]
        assert args[0] == ['xprop', '-id', '0x12345', '_NET_WM_NAME']

def test_window_sensor_linux_escaped_quotes(mock_window_sensor):
    """Verify that regex handles escaped quotes correctly."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            # 1. ID
            MagicMock(returncode=0, stdout="_NET_ACTIVE_WINDOW(WINDOW): window id # 0x12345\n"),
            # 2. _NET_WM_NAME with escaped quotes: "My \"Cool\" Window"
            # Note: In raw string, \\" means literal backslash then quote
            MagicMock(returncode=0, stdout='_NET_WM_NAME(UTF8_STRING) = "My \\"Cool\\" Window"\n')
        ]

        title = mock_window_sensor.get_active_window()
        # The expected output should have unescaped quotes
        assert title == 'My "Cool" Window'

def test_window_sensor_linux_fallback_wm_name(mock_window_sensor):
    """Verify fallback to WM_NAME if _NET_WM_NAME fails."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            # 1. ID
            MagicMock(returncode=0, stdout="_NET_ACTIVE_WINDOW(WINDOW): window id # 0x12345\n"),
            # 2. _NET_WM_NAME fails (returncode 1 or empty)
            MagicMock(returncode=1, stdout=""),
            # 3. WM_NAME succeeds
            MagicMock(returncode=0, stdout='WM_NAME(STRING) = "Legacy Title"\n')
        ]

        title = mock_window_sensor.get_active_window()
        assert title == "Legacy Title"

        # Verify calls
        assert mock_run.call_count == 3
        args_net, _ = mock_run.call_args_list[1]
        assert args_net[0] == ['xprop', '-id', '0x12345', '_NET_WM_NAME']
        args_wm, _ = mock_run.call_args_list[2]
        assert args_wm[0] == ['xprop', '-id', '0x12345', 'WM_NAME']
import unittest
from unittest.mock import MagicMock
import sys
import os

# Ensure repo root is in path
sys.path.append(os.getcwd())

import config
from sensors.window_sensor import WindowSensor

class TestPrivacyScrubberFixes(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.sensor = WindowSensor(self.mock_logger)

    def test_concatenated_keywords_do_not_exist(self):
        """
        Verify that concatenated keywords are GONE.
        """
        keywords = config.SENSITIVE_APP_KEYWORDS

        found_credit_card_password = False
        found_setting_bank = False

        for k in keywords:
            if "Credit CardPassword" in k:
                found_credit_card_password = True
            if "SettingBank" in k:
                found_setting_bank = True

        self.assertFalse(found_credit_card_password, "Bug fixed: 'Credit CardPassword' should NOT exist")
        self.assertFalse(found_setting_bank, "Bug fixed: 'SettingBank' should NOT exist")

    def test_missing_keywords_are_restored(self):
        """
        Verify that 'Settings' and 'Credit Card' are properly redacted.
        """
        # "System Settings" should NOW be redacted
        title = "System Settings"
        sanitized = self.sensor._sanitize_title(title)
        self.assertEqual(sanitized, "[REDACTED]", "'System Settings' should be redacted")

        # "Credit Card Statement" should be redacted
        title = "Credit Card Statement"
        sanitized = self.sensor._sanitize_title(title)
        self.assertEqual(sanitized, "[REDACTED]", "'Credit Card Statement' should be redacted")

    def test_duplicates_removed(self):
        """
        Ideally, we shouldn't have exact duplicates.
        """
        keywords = config.SENSITIVE_APP_KEYWORDS
        self.assertEqual(len(keywords), len(set(keywords)), "Keywords list should not have duplicates")

if __name__ == '__main__':
    unittest.main()
