import pytest
from core.intervention_library import InterventionLibrary

class TestInterventionLibraryCoverage:
    @pytest.fixture
    def lib(self):
        return InterventionLibrary()

    def test_get_intervention_by_id_found(self, lib):
        """Test retrieving an existing intervention by ID."""
        intervention = lib.get_intervention_by_id("box_breathing")
        assert intervention is not None
        assert intervention["id"] == "box_breathing"
        assert intervention["tier"] == 2
        assert "sequence" in intervention

    def test_get_intervention_by_id_not_found(self, lib):
        """Test retrieving a non-existent intervention by ID."""
        intervention = lib.get_intervention_by_id("non_existent_id")
        assert intervention is None

    def test_get_interventions_by_category_found(self, lib):
        """Test retrieving interventions by a valid category."""
        physio = lib.get_interventions_by_category("physiology")
        assert len(physio) > 0
        for i in physio:
            assert "id" in i

        # Verify specific known interventions exist
        ids = [i["id"] for i in physio]
        assert "box_breathing" in ids
        assert "shoulder_drop" in ids

    def test_get_interventions_by_category_not_found(self, lib):
        """Test retrieving interventions by an invalid category."""
        empty = lib.get_interventions_by_category("invalid_category")
        assert empty == []

    def test_get_interventions_by_category_case_insensitive(self, lib):
        """Test that category lookup is case insensitive."""
        physio = lib.get_interventions_by_category("PhYsIoLoGy")
        assert len(physio) > 0

    def test_get_interventions_by_tier(self, lib):
        """Test retrieving interventions by tier."""
        tier1 = lib.get_interventions_by_tier(1)
        assert len(tier1) > 0
        for i in tier1:
            assert i["tier"] == 1

        tier3 = lib.get_interventions_by_tier(3)
        assert len(tier3) > 0
        ids = [i["id"] for i in tier3]
        assert "cold_water" in ids

    def test_get_random_intervention_all(self, lib):
        """Test getting a random intervention from the entire library."""
        # Run multiple times to ensure we don't crash
        for _ in range(10):
            i = lib.get_random_intervention()
            assert i is not None
            assert "id" in i

    def test_get_random_intervention_filtered(self, lib):
        """Test getting a random intervention with filters."""
        # Category only
        i_cat = lib.get_random_intervention(category="sensory")
        assert i_cat is not None

        # Verify it belongs to sensory category (requires manual check against library structure)
        sensory_ids = [x["id"] for x in lib.library["sensory"]]
        assert i_cat["id"] in sensory_ids

        # Tier only
        i_tier = lib.get_random_intervention(tier=3)
        assert i_tier is not None
        assert i_tier["tier"] == 3

        # Both
        i_both = lib.get_random_intervention(category="physiology", tier=2)
        assert i_both is not None
        # box_breathing or stand_reset
        assert i_both["id"] in ["box_breathing", "stand_reset"]

    def test_get_random_intervention_no_match(self, lib):
        """Test getting a random intervention when no match exists."""
        # Tier 5 doesn't exist
        i = lib.get_random_intervention(tier=5)
        assert i is None

        # Empty category
        i = lib.get_random_intervention(category="invalid")
        assert i is None

    def test_get_all_interventions_info(self, lib):
        """Test the string formatting for LMM prompt."""
        info = lib.get_all_interventions_info()
        assert isinstance(info, str)
        assert len(info) > 0

        # Check format "[Category]: id1, id2"
        assert "[Physiology]:" in info
        assert "box_breathing" in info
        assert "[Sensory]:" in info
