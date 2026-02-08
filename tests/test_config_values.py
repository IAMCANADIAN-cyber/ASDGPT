import config
import pytest

def test_reflexive_triggers_contain_new_games():
    triggers = config.REFLEXIVE_WINDOW_TRIGGERS
    assert "Epic Games Launcher" in triggers
    assert "Battle.net" in triggers
    assert triggers["Epic Games Launcher"] == "distraction_alert"
    assert triggers["Battle.net"] == "distraction_alert"
