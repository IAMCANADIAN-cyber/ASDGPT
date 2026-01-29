import unittest
from core.lmm_interface import LMMInterface
from core.intervention_library import InterventionLibrary

class TestPromptConstruction(unittest.TestCase):
    def test_prompt_contains_critical_instructions(self):
        # Initialize
        lib = InterventionLibrary()
        lmm = LMMInterface(intervention_library=lib)

        # Get the prompt
        prompt = lmm.SYSTEM_INSTRUCTION

        # Critical checks
        self.assertIn("Audio Pitch Variance", prompt)
        self.assertIn("Speech Rate", prompt)
        self.assertIn("Active Window", prompt)
        self.assertIn("doom-scrolling", prompt)
        self.assertIn("{interventions_list}", lmm.BASE_SYSTEM_INSTRUCTION) # Ensure placeholder exists in base
        self.assertNotIn("{interventions_list}", prompt) # Ensure placeholder is replaced in final

        # Check if intervention IDs are injected
        interventions = lib.get_all_interventions_info()
        self.assertIn(interventions, prompt)

        # Check JSON structure guidance
        self.assertIn('"state_estimation"', prompt)
        self.assertIn('"arousal"', prompt)

    def test_prompt_length_sanity(self):
        lmm = LMMInterface()
        prompt = lmm.SYSTEM_INSTRUCTION
        self.assertTrue(len(prompt) > 500, "Prompt seems too short")

if __name__ == '__main__':
    unittest.main()
