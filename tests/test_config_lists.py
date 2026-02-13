import pytest
import config
import os
import json
from unittest.mock import patch, MagicMock
from tools.config_gui import ConfigGUI, ListEditor
import tkinter as tk

class TestConfigLists:
    def test_distraction_apps_default(self):
        """Verify defaults are loaded correctly."""
        assert isinstance(config.DISTRACTION_APPS, list)
        assert "Steam" in config.DISTRACTION_APPS
        assert "Reddit" in config.DISTRACTION_APPS

    def test_focus_apps_default(self):
        """Verify defaults are loaded correctly."""
        assert isinstance(config.FOCUS_APPS, list)
        assert "VS Code" in config.FOCUS_APPS

    @patch('tools.config_gui.ttk.Treeview')
    @patch('tools.config_gui.ttk.Entry')
    def test_list_editor_logic(self, mock_entry, mock_treeview):
        """Verify ListEditor logic (add/delete)."""
        root = MagicMock()
        data = ["Item1", "Item2"]
        editor = ListEditor(root, data=data)

        # Verify initial data
        assert editor.get_data() == ["Item1", "Item2"]

        # Test Add
        editor.entry = MagicMock()
        editor.entry.get.return_value = "Item3"
        editor.add_item()
        assert "Item3" in editor.get_data()

        # Test Delete
        editor.tree.selection.return_value = ["I001"]
        editor.tree.item.return_value = {'values': ["Item1"]}
        editor.delete_item()
        assert "Item1" not in editor.get_data()

    def test_config_gui_structure(self):
        """Verify that ConfigGUI initializes the new editors."""
        root = MagicMock()
        # Mocking os.path.exists to avoid trying to load real config
        with patch('os.path.exists', return_value=False):
            app = ConfigGUI(root)

            assert hasattr(app, 'distraction_editor')
            assert hasattr(app, 'focus_editor')
            assert hasattr(app, 'triggers_editor')
            assert hasattr(app, 'privacy_editor')
