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
