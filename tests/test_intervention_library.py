import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.intervention_library import InterventionLibrary

class TestInterventionLibrary(unittest.TestCase):
    def setUp(self):
        self.lib = InterventionLibrary()

    def test_get_intervention_by_id_found(self):
        intervention = self.lib.get_intervention_by_id("box_breathing")
        self.assertIsNotNone(intervention)
        self.assertEqual(intervention["id"], "box_breathing")
        self.assertIn("sequence", intervention)

    def test_get_intervention_by_id_not_found(self):
        intervention = self.lib.get_intervention_by_id("non_existent_id_12345")
        self.assertIsNone(intervention)

    def test_get_interventions_by_category_found(self):
        cat_list = self.lib.get_interventions_by_category("physiology")
        self.assertTrue(len(cat_list) >= 4)
        for item in cat_list:
            # Note: We can't strictly check the category field inside the item because the structure
            # is {category: [list_of_items]}. The items themselves don't explicitly store their category string
            # in the current data structure, they are just in the list under that key.
            # But we can verify they are valid intervention objects
            self.assertIn("id", item)
            self.assertIn("tier", item)

    def test_get_interventions_by_category_not_found(self):
        cat_list = self.lib.get_interventions_by_category("invalid_category")
        self.assertEqual(cat_list, [])

    def test_get_interventions_by_tier(self):
        tier_3_list = self.lib.get_interventions_by_tier(3)
        self.assertTrue(len(tier_3_list) > 0)
        for item in tier_3_list:
            self.assertEqual(item["tier"], 3)

        tier_99_list = self.lib.get_interventions_by_tier(99)
        self.assertEqual(tier_99_list, [])

    def test_get_random_intervention_basic(self):
        rand_i = self.lib.get_random_intervention()
        self.assertIsNotNone(rand_i)
        self.assertIn("id", rand_i)

    def test_get_random_intervention_filtered(self):
        # Filter by category
        rand_cat = self.lib.get_random_intervention(category="cognitive")
        self.assertIsNotNone(rand_cat)
        # Verify it actually belongs to cognitive
        # We can check by seeing if it's in the cognitive list
        cog_list = self.lib.get_interventions_by_category("cognitive")
        self.assertIn(rand_cat, cog_list)

        # Filter by tier
        rand_tier = self.lib.get_random_intervention(tier=1)
        self.assertIsNotNone(rand_tier)
        self.assertEqual(rand_tier["tier"], 1)

        # Filter by both
        rand_both = self.lib.get_random_intervention(category="physiology", tier=2)
        self.assertIsNotNone(rand_both)
        # Check against physiology list
        phys_list = self.lib.get_interventions_by_category("physiology")
        self.assertIn(rand_both, phys_list)
        self.assertEqual(rand_both["tier"], 2)

    def test_get_random_intervention_no_match(self):
        rand_none = self.lib.get_random_intervention(category="physiology", tier=99)
        self.assertIsNone(rand_none)

    def test_get_all_interventions_info(self):
        info = self.lib.get_all_interventions_info()
        self.assertIsInstance(info, str)
        self.assertIn("Physiology", info)
        self.assertIn("box_breathing", info)

    def test_verify_critical_interventions(self):
        # Verify specific IDs mentioned in requirements or other tests exist
        critical_ids = [
            "doom_scroll_breaker",
            "arousal_redirect",
            "posture_water_reset",
            "meltdown_prevention",
            "cold_water"
        ]
        for vid in critical_ids:
            self.assertIsNotNone(self.lib.get_intervention_by_id(vid), f"Missing critical intervention: {vid}")

if __name__ == '__main__':
    unittest.main()
