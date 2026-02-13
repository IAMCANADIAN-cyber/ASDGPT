import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure repo root is in path
sys.path.append(os.getcwd())

from sensors.window_sensor import WindowSensor
import config

class TestWindowPrivacyExpanded(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.sensor = WindowSensor(self.mock_logger)

    def test_financial_keywords(self):
        # These should now be redacted by default config
        cases = [
            ("Chase Bank - Login", "[REDACTED]"),
            ("Bank of America", "[REDACTED]"),
            ("My Crypto Wallet", "[REDACTED]"),
            ("IRS Tax Return 2025.pdf", "[REDACTED]"),
            ("TurboTax", "[REDACTED]"),
            ("Financial Statement.xlsx", "[REDACTED]"),
            ("Credit Card Bill", "[REDACTED]"),
            ("SSN Application", "[REDACTED]"),
            ("Social Security Administration", "[REDACTED]")
        ]

        for input_title, expected in cases:
            with self.subTest(title=input_title):
                self.assertEqual(self.sensor._sanitize_title(input_title), expected)

    def test_legacy_keywords(self):
        # Verify old keywords still work
        cases = [
            ("KeePassXC", "[REDACTED]"),
            ("LastPass Vault", "[REDACTED]"),
            ("1Password", "[REDACTED]"),
            ("Bitwarden", "[REDACTED]"),
            ("Incognito Tab", "[REDACTED]"),
            ("InPrivate Browsing", "[REDACTED]"),
            ("Tor Browser", "[REDACTED]"),
            ("Private Document", "[REDACTED]")
        ]

        for input_title, expected in cases:
            with self.subTest(title=input_title):
                self.assertEqual(self.sensor._sanitize_title(input_title), expected)

    def test_generic_safe_titles(self):
        # Verify we haven't broken normal titles
        cases = [
            ("Google Search", "Google Search"),
            ("Python Documentation", "Python Documentation"),
            ("Visual Studio Code", "Visual Studio Code"),
            ("Spotify", "Spotify"),
            ("Minecraft", "Minecraft")
        ]

        for input_title, expected in cases:
            with self.subTest(title=input_title):
                self.assertEqual(self.sensor._sanitize_title(input_title), expected)

    def test_custom_config_override(self):
        # Verify that if we patch config, it respects the patch
        with patch('sensors.window_sensor.config.SENSITIVE_APP_KEYWORDS', ["Minecraft"]):
            self.assertEqual(self.sensor._sanitize_title("Minecraft"), "[REDACTED]")
            # Default keywords should NOT work if list is overridden completely
            self.assertEqual(self.sensor._sanitize_title("Chase Bank"), "Chase Bank")

if __name__ == '__main__':
    unittest.main()
