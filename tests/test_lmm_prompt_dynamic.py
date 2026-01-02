import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.lmm_interface import LMMInterface
from core.intervention_library import InterventionLibrary

class TestLMMDynamicPrompt(unittest.TestCase):
    def test_prompt_contains_default_interventions(self):
        """Test that the default interventions are present in the generated system prompt."""
        lmm = LMMInterface()
        prompt = lmm.SYSTEM_INSTRUCTION

        # Check for known categories and IDs
        self.assertIn("[Physiology]", prompt)
        self.assertIn("box_breathing", prompt)
        self.assertIn("doom_scroll_breaker", prompt)
        self.assertIn("public_persona_prompt", prompt)

    def test_prompt_updates_with_new_intervention(self):
        """Test that adding a new intervention to the library updates the LMM prompt."""

        # Create a library and add a mock intervention
        lib = InterventionLibrary()

        # Manually inject a new intervention for testing
        # (Since InterventionLibrary doesn't have an add method yet, we modify the dict directly)
        lib.library["testing_category"] = [
            {"id": "test_intervention_unique_id_123", "tier": 1, "description": "Test", "sequence": []}
        ]

        lmm = LMMInterface(intervention_library=lib)
        prompt = lmm.SYSTEM_INSTRUCTION

        self.assertIn("[Testing_category]", prompt)
        self.assertIn("test_intervention_unique_id_123", prompt)

    def test_prompt_formatting(self):
        """Test that the formatting looks correct (newlines, etc)."""
        lmm = LMMInterface()
        prompt = lmm.SYSTEM_INSTRUCTION

        # Should not see the placeholder anymore
        self.assertNotIn("{interventions_list}", prompt)

        # Should contain the intro text
        self.assertIn("Available Interventions (by ID):", prompt)

        # Verify JSON example has correct single braces, not double
        self.assertIn('"state_estimation": {', prompt)
        self.assertNotIn('"state_estimation": {{', prompt)

if __name__ == '__main__':
    unittest.main()
