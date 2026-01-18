<<<<<<< HEAD
import pytest
from core.intervention_library import InterventionLibrary

class TestInterventionLibrary:
    def setup_method(self):
        self.lib = InterventionLibrary()

    def test_get_intervention_by_id_exists(self):
        intervention = self.lib.get_intervention_by_id("box_breathing")
        assert intervention is not None
        assert intervention["id"] == "box_breathing"
        assert intervention["tier"] == 2
        assert len(intervention["sequence"]) > 0

    def test_get_intervention_by_id_missing(self):
        intervention = self.lib.get_intervention_by_id("non_existent_intervention")
        assert intervention is None

    def test_get_interventions_by_category_exists(self):
        interventions = self.lib.get_interventions_by_category("physiology")
        assert len(interventions) > 0
        for intervention in interventions:
            assert "physiology" in self.lib.library
            # Check if this intervention is indeed in the physiology list
            assert intervention in self.lib.library["physiology"]

    def test_get_interventions_by_category_missing(self):
        interventions = self.lib.get_interventions_by_category("non_existent_category")
        assert interventions == []

    def test_get_interventions_by_tier(self):
        tier_3_interventions = self.lib.get_interventions_by_tier(3)
        assert len(tier_3_interventions) > 0
        for intervention in tier_3_interventions:
            assert intervention["tier"] == 3

    def test_get_random_intervention_filters(self):
        # Test category filter
        rand_cat = self.lib.get_random_intervention(category="sensory")
        if rand_cat:
             assert rand_cat in self.lib.library["sensory"]

        # Test tier filter
        rand_tier = self.lib.get_random_intervention(tier=3)
        if rand_tier:
            assert rand_tier["tier"] == 3

        # Test both
        rand_both = self.lib.get_random_intervention(category="physiology", tier=2)
        if rand_both:
            assert rand_both in self.lib.library["physiology"]
            assert rand_both["tier"] == 2

    def test_get_random_intervention_no_match(self):
        # Assuming no tier 10 exists
        intervention = self.lib.get_random_intervention(tier=10)
        assert intervention is None

    def test_get_all_interventions_info_format(self):
        info = self.lib.get_all_interventions_info()
        assert isinstance(info, str)
        assert len(info) > 0
        assert "[Physiology]" in info or "[physiology]" in info.lower()
        assert "box_breathing" in info

    def test_critical_interventions_exist(self):
        # Verify that critical interventions used in logic are present
        critical_ids = [
            "box_breathing",
            "posture_water_reset",
            "meltdown_prevention",
            "doom_scroll_breaker"
        ]
        for i_id in critical_ids:
            assert self.lib.get_intervention_by_id(i_id) is not None, f"Missing critical intervention: {i_id}"
=======
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.intervention_library import InterventionLibrary

class TestInterventionLibrary(unittest.TestCase):
    def setUp(self):
        self.lib = InterventionLibrary()

    def test_get_intervention_by_id_found(self):
        """Test retrieving an existing intervention by ID."""
        # Test with a known ID from the library
        intervention = self.lib.get_intervention_by_id("box_breathing")
        self.assertIsNotNone(intervention)
        self.assertEqual(intervention["id"], "box_breathing")
        self.assertEqual(intervention["tier"], 2)
        self.assertTrue(len(intervention["sequence"]) > 0)

    def test_get_intervention_by_id_not_found(self):
        """Test retrieving a non-existent intervention ID."""
        intervention = self.lib.get_intervention_by_id("non_existent_id_999")
        self.assertIsNone(intervention)

    def test_get_interventions_by_category_found(self):
        """Test retrieving interventions by a valid category."""
        category = "physiology"
        interventions = self.lib.get_interventions_by_category(category)
        self.assertTrue(len(interventions) > 0)
        for i in interventions:
            # We can't easily check category in the item itself as it's not stored in the item dict,
            # but we can verify they are the ones we expect if needed.
            # For now, just checking we got a list of dicts.
            self.assertIn("id", i)

    def test_get_interventions_by_category_case_insensitive(self):
        """Test retrieving interventions by category is case insensitive."""
        interventions = self.lib.get_interventions_by_category("PHYSIOLOGY")
        self.assertTrue(len(interventions) > 0)

    def test_get_interventions_by_category_not_found(self):
        """Test retrieving interventions by an invalid category."""
        interventions = self.lib.get_interventions_by_category("invalid_category")
        self.assertEqual(interventions, [])

    def test_get_interventions_by_tier(self):
        """Test retrieving interventions by tier."""
        tier = 3
        interventions = self.lib.get_interventions_by_tier(tier)
        self.assertTrue(len(interventions) > 0)
        for i in interventions:
            self.assertEqual(i["tier"], tier)

    def test_get_interventions_by_tier_empty(self):
        """Test retrieving interventions for a tier that has no items."""
        interventions = self.lib.get_interventions_by_tier(999)
        self.assertEqual(interventions, [])

    @patch('random.choice')
    def test_get_random_intervention_no_filters(self, mock_choice):
        """Test getting a random intervention without filters."""
        # Setup mock to return the first item it receives
        def side_effect(candidates):
            return candidates[0]
        mock_choice.side_effect = side_effect

        intervention = self.lib.get_random_intervention()
        self.assertIsNotNone(intervention)
        self.assertTrue(mock_choice.called)

    @patch('random.choice')
    def test_get_random_intervention_with_category(self, mock_choice):
        """Test getting a random intervention with category filter."""
        mock_choice.side_effect = lambda x: x[0]

        intervention = self.lib.get_random_intervention(category="sensory")
        self.assertIsNotNone(intervention)
        # Verify the candidate list passed to random.choice only had sensory items
        args, _ = mock_choice.call_args
        candidates = args[0]
        # We verify that 'visual_scan' (a known sensory item) is in the candidates
        # or that all candidates are from the sensory list.
        sensory_list = self.lib.library["sensory"]
        for c in candidates:
             self.assertIn(c, sensory_list)

    @patch('random.choice')
    def test_get_random_intervention_with_tier(self, mock_choice):
        """Test getting a random intervention with tier filter."""
        mock_choice.side_effect = lambda x: x[0]

        target_tier = 1
        intervention = self.lib.get_random_intervention(tier=target_tier)
        self.assertIsNotNone(intervention)
        self.assertEqual(intervention["tier"], target_tier)

    def test_get_random_intervention_no_match(self):
        """Test getting a random intervention when no match exists."""
        intervention = self.lib.get_random_intervention(category="physiology", tier=99)
        self.assertIsNone(intervention)

    def test_get_all_interventions_info(self):
        """Test the string formatting of get_all_interventions_info."""
        info = self.lib.get_all_interventions_info()
        self.assertIsInstance(info, str)
        self.assertIn("[Physiology]:", info)
        self.assertIn("box_breathing", info)
        # Check for new categories/items
        self.assertIn("[Recovery]:", info)
        self.assertIn("meltdown_prevention", info)

    def test_integrity_of_library(self):
        """Verify that all interventions in the library have the required keys."""
        required_keys = ["id", "tier", "description", "sequence"]
        for category, items in self.lib.library.items():
            for item in items:
                for key in required_keys:
                    self.assertIn(key, item, f"Item {item.get('id', 'unknown')} in {category} missing key {key}")
                self.assertIsInstance(item["sequence"], list, f"Sequence for {item['id']} is not a list")
                self.assertGreater(len(item["sequence"]), 0, f"Sequence for {item['id']} is empty")

    def test_verify_known_ids(self):
        """Explicitly check for the existence of specific high-value interventions."""
        expected_ids = [
            "box_breathing",
            "doom_scroll_breaker",
            "arousal_redirect",
            "posture_water_reset",
            "meltdown_prevention"
        ]
        for i_id in expected_ids:
            self.assertIsNotNone(self.lib.get_intervention_by_id(i_id), f"Critical intervention {i_id} missing")

if __name__ == '__main__':
    unittest.main()
>>>>>>> origin/main
