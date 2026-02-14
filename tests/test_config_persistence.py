import unittest
import json
import os
import shutil
import importlib
from unittest.mock import MagicMock
import config
from core.logic_engine import LogicEngine

class TestConfigPersistence(unittest.TestCase):
    def setUp(self):
        # Backup existing config.json
        self.config_path = os.path.join("user_data", "config.json")
        self.backup_path = self.config_path + ".bak"
        if os.path.exists(self.config_path):
            shutil.copy2(self.config_path, self.backup_path)

        # Ensure user_data dir exists
        os.makedirs("user_data", exist_ok=True)

        # Store original config values to restore later
        self.original_distraction = getattr(config, 'DISTRACTION_APPS', [])
        self.original_focus = getattr(config, 'FOCUS_APPS', [])
        self.original_reflexes = getattr(config, 'REFLEXIVE_WINDOW_TRIGGERS', {})

    def tearDown(self):
        # Restore config.json
        if os.path.exists(self.backup_path):
            shutil.move(self.backup_path, self.config_path)
        elif os.path.exists(self.config_path):
            os.remove(self.config_path)

        # Restore in-memory config
        # We can try to reload, but since we modify user_data/config.json, reloading might pick up bad state if we don't clean up first.
        # But we just cleaned up config.json above.
        importlib.reload(config)

    def test_load_custom_apps_from_json(self):
        """Verify that DISTRACTION_APPS and FOCUS_APPS are loaded from user_data/config.json."""

        custom_config = {
            "DISTRACTION_APPS": ["TestDistractionGame", "AnotherWaster"],
            "FOCUS_APPS": ["SuperCodeEditor", "MyThesis.docx"],
            "REFLEXIVE_WINDOW_TRIGGERS": {
                "SpecificBadApp": "urgent_alert"
            }
        }

        with open(self.config_path, 'w') as f:
            json.dump(custom_config, f)

        # Reload config to pick up changes
        importlib.reload(config)

        # Verify values
        self.assertEqual(config.DISTRACTION_APPS, ["TestDistractionGame", "AnotherWaster"])
        self.assertEqual(config.FOCUS_APPS, ["SuperCodeEditor", "MyThesis.docx"])
        self.assertEqual(config.REFLEXIVE_WINDOW_TRIGGERS, {"SpecificBadApp": "urgent_alert"})

    def test_logic_engine_respects_custom_distraction(self):
        """Verify LogicEngine uses the loaded distraction list."""

        # rigorous setup: write config, reload, init engine
        custom_config = {
            "DISTRACTION_APPS": ["DoomScrollApp"],
            "FOCUS_APPS": [],
            "REFLEXIVE_WINDOW_TRIGGERS": {}
        }
        with open(self.config_path, 'w') as f:
            json.dump(custom_config, f)

        importlib.reload(config)

        engine = LogicEngine(logger=MagicMock())

        # Test detection
        # LogicEngine._check_window_reflexes returns "distraction_alert" for items in DISTRACTION_APPS
        result = engine._check_window_reflexes("DoomScrollApp - Home")
        self.assertEqual(result, "distraction_alert")

        # Test non-match
        result = engine._check_window_reflexes("Notepad")
        self.assertIsNone(result)

    def test_logic_engine_respects_custom_focus(self):
        """Verify LogicEngine uses the loaded focus list to suppress distractions."""

        # Setup: Focus App "IDE" and Distraction App "Social"
        # If active window contains "IDE", it should suppress even if "Social" is somehow matched (unlikely in real world but Logic checks Focus first)
        # Actually, LogicEngine check order:
        # 1. Custom Triggers (REFLEXIVE_WINDOW_TRIGGERS) -> returns ID
        # 2. Focus Apps -> returns None (Safe)
        # 3. Distraction Apps -> returns "distraction_alert"

        custom_config = {
            "DISTRACTION_APPS": ["SocialMedia"],
            "FOCUS_APPS": ["MyWorkIDE"],
            "REFLEXIVE_WINDOW_TRIGGERS": {}
        }
        with open(self.config_path, 'w') as f:
            json.dump(custom_config, f)

        importlib.reload(config)

        engine = LogicEngine(logger=MagicMock())

        # 1. Check Distraction
        self.assertEqual(engine._check_window_reflexes("SocialMedia Feed"), "distraction_alert")

        # 2. Check Focus
        # Should return None (explicitly safe)
        self.assertIsNone(engine._check_window_reflexes("MyWorkIDE - Project"))

        # 3. Check Focus taking precedence?
        # If a window title contains BOTH, Focus should win.
        # "MyWorkIDE - Researching on SocialMedia"
        self.assertIsNone(engine._check_window_reflexes("MyWorkIDE - Researching on SocialMedia"))

    def test_logic_engine_respects_custom_triggers(self):
        """Verify LogicEngine uses the loaded custom triggers."""

        custom_config = {
            "REFLEXIVE_WINDOW_TRIGGERS": {
                "CriticalGame": "force_shutdown_simulation"
            }
        }
        with open(self.config_path, 'w') as f:
            json.dump(custom_config, f)

        importlib.reload(config)

        engine = LogicEngine(logger=MagicMock())

        # Should return the specific intervention ID
        self.assertEqual(engine._check_window_reflexes("Playing CriticalGame"), "force_shutdown_simulation")

if __name__ == '__main__':
    unittest.main()
