import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure repo root is in path
sys.path.append(os.getcwd())

from sensors.window_sensor import WindowSensor
import config

class TestPrivacyFuzzy(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.sensor = WindowSensor(self.mock_logger)

    def test_fuzzy_matching_typos(self):
        """Test that window titles with typos close to sensitive keywords are redacted."""
        # Config has: "Keepass", "LastPass", "1Password", "Bitwarden", etc.

        cases = [
            ("KePass XC", "[REDACTED]"),      # Case + Space variation
            ("KeePas - Database", "[REDACTED]"), # Typo (missing s)
            ("LastPas Vault", "[REDACTED]"),  # Typo (missing s)
            ("1Passwrd", "[REDACTED]"),       # Typo (missing o)
            ("Bitwardn", "[REDACTED]"),       # Typo (missing e)
            ("InCognito Tab", "[REDACTED]"),  # Mixed case
            ("Tor Brower", "[REDACTED]"),     # Typo (missing s)
        ]

        for input_title, expected in cases:
            with self.subTest(title=input_title):
                sanitized = self.sensor._sanitize_title(input_title)
                self.assertEqual(sanitized, expected, f"Failed to redact '{input_title}'")

    def test_fuzzy_matching_false_positives(self):
        """Test that normal words similar to keywords are NOT redacted unnecessarily."""
        # "Bank" is a keyword. "Blank" is close but should arguably NOT be redacted if context is clear?
        # Actually, "Blank" distance to "Bank" is 1 char insertion.
        # difflib.get_close_matches cutoff=0.85 might be strict enough.
        # "Bank" (4 chars). "Blank" (5 chars). Ratio is 2*4 / (4+5) = 8/9 = 0.88.
        # So "Blank" MIGHT be redacted if we are not careful.
        # But let's check what we expect. "Blank Document" -> "Blank Document".

        cases = [
            ("Blank Document", "Blank Document"),
            ("Tank Game", "Tank Game"),           # "Tank" vs "Bank" (1 char sub). Ratio 0.75?
            ("Password Generator", "[REDACTED]"), # "Password" is keyword
            ("Passport Application", "Passport Application"), # "Passport" vs "Password"?
        ]

        for input_title, expected in cases:
            with self.subTest(title=input_title):
                sanitized = self.sensor._sanitize_title(input_title)
                # We log if it fails just to see behavior, as fuzzy logic is approximate
                if sanitized != expected:
                    print(f"Warning: '{input_title}' became '{sanitized}' (Expected: '{expected}')")

                # We assert mostly for regression, but fuzzy logic might need tuning.
                # If "Blank" is redacted, we might need to tune cutoff or length check.
                self.assertEqual(sanitized, expected, f"False positive/negative for '{input_title}'")

if __name__ == '__main__':
    unittest.main()
