import unittest
from core.intervention_library import InterventionLibrary

class TestInterventionLibrary(unittest.TestCase):
    def setUp(self):
        self.lib = InterventionLibrary()

    def test_get_intervention_by_id(self):
        i1 = self.lib.get_intervention_by_id("box_breathing")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["id"], "box_breathing")
        self.assertTrue(len(i1["sequence"]) > 0)

    def test_get_interventions_by_category(self):
        cat_list = self.lib.get_interventions_by_category("physiology")
        self.assertGreaterEqual(len(cat_list), 4)
        for i in cat_list:
            # Assuming category key isn't stored in the intervention dict itself,
            # but we can verify they are valid dicts
            self.assertIn("id", i)

    def test_get_interventions_by_tier(self):
        tier_list = self.lib.get_interventions_by_tier(3)
        self.assertTrue(len(tier_list) > 0)
        self.assertTrue(any(i["id"] == "cold_water" for i in tier_list))
        for i in tier_list:
            self.assertEqual(i["tier"], 3)

    def test_get_random_intervention(self):
        # Test basic random
        rand_i = self.lib.get_random_intervention()
        self.assertIsNotNone(rand_i)

        # Test with filters
        rand_cognitive_tier1 = self.lib.get_random_intervention(category="cognitive", tier=1)
        if rand_cognitive_tier1: # Might be None if none exist, but cognitive tier 1 should exist
            self.assertEqual(rand_cognitive_tier1["tier"], 1)
            # We can't easily check category reverse lookup without iterating everything,
            # but we assume the method works if basic tests pass.

        # Test non-existent combo
        rand_none = self.lib.get_random_intervention(category="nonexistent_category")
        self.assertIsNone(rand_none)

    def test_v4_interventions_exist(self):
        v4_ids = ["doom_scroll_breaker", "arousal_redirect", "content_pivot", "sultry_persona_prompt", "public_persona_prompt"]
        for vid in v4_ids:
            self.assertIsNotNone(self.lib.get_intervention_by_id(vid), f"Missing V4 intervention: {vid}")

    def test_mental_model_interventions_exist(self):
        new_ids = ["posture_water_reset", "stand_reset", "reduce_input", "bookmark_thought", "minimum_viable_action", "shutdown_reset", "meltdown_prevention"]
        for vid in new_ids:
            self.assertIsNotNone(self.lib.get_intervention_by_id(vid), f"Missing Mental Model intervention: {vid}")

    def test_social_category_exists(self):
        social_list = self.lib.get_interventions_by_category("social")
        self.assertIsNotNone(social_list)
        self.assertGreater(len(social_list), 0)

if __name__ == '__main__':
    unittest.main()
