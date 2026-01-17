import unittest
from core.intervention_library import InterventionLibrary

class TestInterventionLibrary(unittest.TestCase):
    def setUp(self):
        self.lib = InterventionLibrary()

    def test_get_intervention_by_id(self):
        """Test retrieving a specific intervention by ID."""
        i1 = self.lib.get_intervention_by_id("box_breathing")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["id"], "box_breathing")
        self.assertGreater(len(i1["sequence"]), 0)

        # Test non-existent ID
        self.assertIsNone(self.lib.get_intervention_by_id("non_existent_id"))

    def test_get_interventions_by_category(self):
        """Test retrieving interventions by category."""
        cat_list = self.lib.get_interventions_by_category("physiology")
        self.assertGreaterEqual(len(cat_list), 4)
        for i in cat_list:
            # We don't have a category field in the intervention dict itself,
            # but we can check if they are in the library under that key if we accessed it directly,
            # but here we just check we got a list back.
            self.assertIn("id", i)

        # Test case insensitivity if implemented, or at least standard behavior
        # The implementation uses .lower()
        cat_list_upper = self.lib.get_interventions_by_category("PHYSIOLOGY")
        self.assertEqual(len(cat_list), len(cat_list_upper))

        # Test empty/unknown category
        self.assertEqual(self.lib.get_interventions_by_category("unknown_cat"), [])

    def test_get_interventions_by_tier(self):
        """Test retrieving interventions by tier."""
        tier_3_list = self.lib.get_interventions_by_tier(3)
        self.assertGreater(len(tier_3_list), 0)
        self.assertTrue(any(i["id"] == "cold_water" for i in tier_3_list))

        for i in tier_3_list:
            self.assertEqual(i["tier"], 3)

    def test_get_random_intervention(self):
        """Test random intervention selection with filters."""
        # Test random with specific category and tier
        rand_i = self.lib.get_random_intervention(category="cognitive", tier=1)
        if rand_i:
            self.assertEqual(rand_i["tier"], 1)
            # Verify it's actually from cognitive category
            cog_ids = [x["id"] for x in self.lib.get_interventions_by_category("cognitive")]
            self.assertIn(rand_i["id"], cog_ids)

        # Test return None if no match
        # Assuming no tier 10 exists
        self.assertIsNone(self.lib.get_random_intervention(tier=10))

    def test_get_all_interventions_info(self):
        """Test the string representation for LMM prompts."""
        info = self.lib.get_all_interventions_info()
        self.assertIsInstance(info, str)
        self.assertIn("[Physiology]:", info)
        self.assertIn("box_breathing", info)

    def test_critical_interventions_exist(self):
        """Verify existence of interventions required by other system components."""
        v4_ids = ["doom_scroll_breaker", "arousal_redirect", "content_pivot", "sultry_persona_prompt", "public_persona_prompt"]
        for vid in v4_ids:
            self.assertIsNotNone(self.lib.get_intervention_by_id(vid), f"Missing V4 intervention: {vid}")

        new_ids = ["posture_water_reset", "stand_reset", "reduce_input", "bookmark_thought", "minimum_viable_action", "shutdown_reset", "meltdown_prevention"]
        for vid in new_ids:
             self.assertIsNotNone(self.lib.get_intervention_by_id(vid), f"Missing Mental Model intervention: {vid}")

        social_cat = self.lib.get_interventions_by_category("social")
        self.assertIsNotNone(social_cat)
        self.assertGreater(len(social_cat), 0)

if __name__ == "__main__":
    unittest.main()
