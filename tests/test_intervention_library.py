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
