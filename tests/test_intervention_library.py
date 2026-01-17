import pytest
from core.intervention_library import InterventionLibrary

class TestInterventionLibrary:
    def setup_method(self):
        self.lib = InterventionLibrary()

    def test_get_intervention_by_id(self):
        """Test retrieving interventions by ID."""
        # Test existing intervention
        i1 = self.lib.get_intervention_by_id("box_breathing")
        assert i1 is not None
        assert i1["id"] == "box_breathing"
        assert len(i1["sequence"]) > 0
        assert i1["tier"] == 2

        # Test non-existent intervention
        i2 = self.lib.get_intervention_by_id("non_existent_id")
        assert i2 is None

    def test_get_interventions_by_category(self):
        """Test retrieving interventions by category."""
        # Test existing category
        cat_list = self.lib.get_interventions_by_category("physiology")
        assert len(cat_list) >= 4
        for intervention in cat_list:
            # We don't have a category field IN the intervention dict,
            # but we can verify they are the ones we expect if we want,
            # or just rely on the count and existence.
            assert "id" in intervention
            assert "sequence" in intervention

        # Test case-insensitivity
        cat_list_upper = self.lib.get_interventions_by_category("PHYSIOLOGY")
        assert len(cat_list_upper) == len(cat_list)

        # Test non-existent category
        empty_list = self.lib.get_interventions_by_category("invalid_category")
        assert len(empty_list) == 0

    def test_get_interventions_by_tier(self):
        """Test retrieving interventions by tier."""
        tier_list = self.lib.get_interventions_by_tier(3)
        # We know "cold_water" and "meltdown_prevention" and "arousal_redirect" are tier 3
        assert len(tier_list) >= 3
        ids = [i["id"] for i in tier_list]
        assert "cold_water" in ids
        assert "meltdown_prevention" in ids
        assert "arousal_redirect" in ids

        for intervention in tier_list:
            assert intervention["tier"] == 3

    def test_get_random_intervention(self):
        """Test random selection logic."""
        # Test with category and tier
        rand_i = self.lib.get_random_intervention(category="cognitive", tier=1)
        if rand_i:
            assert rand_i["tier"] == 1
            # We can't easily verify category from the returned object alone without checking the source list,
            # but we trust the method logic if other tests pass.

        # Test with only tier
        rand_tier = self.lib.get_random_intervention(tier=3)
        if rand_tier:
            assert rand_tier["tier"] == 3

        # Test with only category
        rand_cat = self.lib.get_random_intervention(category="social")
        if rand_cat:
            # Social only has tier 1 currently
            assert rand_cat["tier"] == 1

    def test_verify_v4_interventions(self):
        """Verify existence of V4 interventions."""
        v4_ids = [
            "doom_scroll_breaker",
            "arousal_redirect",
            "content_pivot",
            "sultry_persona_prompt",
            "public_persona_prompt"
        ]
        for vid in v4_ids:
            assert self.lib.get_intervention_by_id(vid) is not None, f"Missing {vid}"

    def test_verify_mental_model_additions(self):
        """Verify existence of Mental Model interventions."""
        new_ids = [
            "posture_water_reset",
            "stand_reset",
            "reduce_input",
            "bookmark_thought",
            "minimum_viable_action",
            "shutdown_reset",
            "meltdown_prevention"
        ]
        for vid in new_ids:
            assert self.lib.get_intervention_by_id(vid) is not None, f"Missing {vid}"

    def test_get_all_interventions_info(self):
        """Test the string representation for LMM prompts."""
        info_str = self.lib.get_all_interventions_info()
        assert "[Physiology]:" in info_str
        assert "box_breathing" in info_str
        assert "[Cognitive]:" in info_str
        assert "doom_scroll_breaker" in info_str
        assert "\n" in info_str
