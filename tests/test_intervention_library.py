import pytest
from core.intervention_library import InterventionLibrary

class TestInterventionLibrary:
    def setup_method(self):
        self.lib = InterventionLibrary()

    def test_get_intervention_by_id_exists(self):
        intervention = self.lib.get_intervention_by_id("box_breathing")
        assert intervention is not None
        assert intervention["id"] == "box_breathing"
        assert len(intervention["sequence"]) > 0

    def test_get_intervention_by_id_missing(self):
        intervention = self.lib.get_intervention_by_id("non_existent_id")
        assert intervention is None

    def test_get_interventions_by_category_exists(self):
        interventions = self.lib.get_interventions_by_category("physiology")
        assert len(interventions) >= 1
        for i in interventions:
            assert i["id"] in [x["id"] for x in self.lib.library["physiology"]]

    def test_get_interventions_by_category_missing(self):
        interventions = self.lib.get_interventions_by_category("non_existent_category")
        assert interventions == []

    def test_get_interventions_by_tier(self):
        # We know box_breathing is tier 2
        tier2 = self.lib.get_interventions_by_tier(2)
        ids = [i["id"] for i in tier2]
        assert "box_breathing" in ids

        # Check all returned have correct tier
        for i in tier2:
            assert i["tier"] == 2

    def test_get_random_intervention_filters(self):
        # Filter by category
        i = self.lib.get_random_intervention(category="physiology")
        assert i is not None
        # Verify it belongs to physiology category (by checking list)
        phys_ids = [x["id"] for x in self.lib.library["physiology"]]
        assert i["id"] in phys_ids

        # Filter by tier
        i = self.lib.get_random_intervention(tier=2)
        assert i is not None
        assert i["tier"] == 2

        # Filter by both
        i = self.lib.get_random_intervention(category="physiology", tier=2)
        assert i is not None
        assert i["id"] in phys_ids
        assert i["tier"] == 2

    def test_get_random_intervention_no_match(self):
        # Assuming no tier 100 exists
        i = self.lib.get_random_intervention(tier=100)
        assert i is None

    def test_get_all_interventions_info_format(self):
        info = self.lib.get_all_interventions_info()
        assert isinstance(info, str)
        assert "[Physiology]:" in info
        assert "box_breathing" in info

    def test_critical_interventions_presence(self):
        """Verify key interventions from roadmap/spec are present."""
        critical_ids = [
            "doom_scroll_breaker",
            "arousal_redirect",
            "content_pivot",
            "sultry_persona_prompt",
            "public_persona_prompt",
            "posture_water_reset",
            "stand_reset",
            "reduce_input",
            "bookmark_thought",
            "minimum_viable_action",
            "shutdown_reset",
            "meltdown_prevention"
        ]
        for vid in critical_ids:
            assert self.lib.get_intervention_by_id(vid) is not None, f"Missing {vid}"

    def test_social_category_presence(self):
        social = self.lib.get_interventions_by_category("social")
        assert len(social) > 0
        assert any(i["id"] == "low_stakes_message" for i in social)
