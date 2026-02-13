import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import json
import tempfile
import shutil

# Create better mocks for tkinter classes
class MockWidget:
    def __init__(self, master=None, **kwargs):
        self.master = master
    def pack(self, **kwargs): pass
    def grid(self, **kwargs): pass
    def bind(self, *args, **kwargs): pass
    def delete(self, *args, **kwargs): pass
    def insert(self, *args, **kwargs): pass
    def get(self): return ""
    def set(self, val): pass
    def get_children(self): return []
    def selection(self): return []
    def item(self, item, option=None): return {'values': []}
    def heading(self, *args, **kwargs): pass
    def title(self, val): pass
    def geometry(self, val): pass
    def mainloop(self): pass

class MockFrame(MockWidget):
    pass

class MockTreeview(MockWidget):
    pass

class MockEntry(MockWidget):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.value = ""
    def get(self):
        return self.value
    def insert(self, index, string, **kwargs):
        self.value = string
    def delete(self, first, last=None, **kwargs):
        self.value = ""
    def set(self, val):
        self.value = val

class MockNotebook(MockWidget):
    def add(self, child, **kw): pass

# Setup sys.modules mocks
mock_ttk = MagicMock()
mock_ttk.Frame = MockFrame
mock_ttk.Treeview = MockTreeview
mock_ttk.Entry = MockEntry
mock_ttk.Notebook = MockNotebook
mock_ttk.Label = MockWidget
mock_ttk.Button = MockWidget
mock_ttk.Combobox = MockWidget

mock_tk = MagicMock()
mock_tk.Tk = MockWidget
mock_tk.Frame = MockFrame
mock_tk.ttk = mock_ttk
sys.modules['tkinter'] = mock_tk
sys.modules['tkinter.ttk'] = mock_ttk

sys.modules['tkinter.messagebox'] = MagicMock()

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import config_gui after mocking
from tools.config_gui import ConfigGUI, DictionaryEditor, ListEditor
import config

class TestConfigGUILogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'config.json')

        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        os.makedirs("user_data", exist_ok=True)

        # Create a dummy config file
        self.initial_config = {
            "AUDIO_THRESHOLD_HIGH": 0.8,
            "REFLEXIVE_WINDOW_TRIGGERS": {"TestApp": "test_intervention"},
            "SENSITIVE_APP_KEYWORDS": ["TestSensitive", "Bank"]
        }
        with open(os.path.join("user_data", "config.json"), 'w') as f:
            json.dump(self.initial_config, f)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_load_config(self):
        mock_root = MockWidget()
        app = ConfigGUI(mock_root)

        self.assertEqual(app.config_data.get("AUDIO_THRESHOLD_HIGH"), 0.8)
        self.assertEqual(app.config_data.get("REFLEXIVE_WINDOW_TRIGGERS"), {"TestApp": "test_intervention"})
        self.assertIn("TestSensitive", app.config_data.get("SENSITIVE_APP_KEYWORDS"))

    def test_save_config_with_triggers(self):
        mock_root = MockWidget()
        app = ConfigGUI(mock_root)

        # Verify editor initialized
        self.assertEqual(app.triggers_editor.data, {"TestApp": "test_intervention"})

        # Modify data
        app.triggers_editor.data = {"NewApp": "new_intervention"}

        # Clear entries
        app.entries = {}

        app.save_config()

        with open(os.path.join("user_data", "config.json"), 'r') as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data["REFLEXIVE_WINDOW_TRIGGERS"], {"NewApp": "new_intervention"})

    def test_save_config_with_privacy(self):
        mock_root = MockWidget()
        app = ConfigGUI(mock_root)

        # Check if privacy editor exists
        self.assertTrue(hasattr(app, 'privacy_editor'), "ConfigGUI should have 'privacy_editor' attribute")

        # Verify initial data load
        self.assertEqual(set(app.privacy_editor.data), set(["TestSensitive", "Bank"]))

        # Add a new keyword
        app.privacy_editor.data.append("NewSecretApp")

        # Clear entries
        app.entries = {}

        # Save
        app.save_config()

        # Verify persistence
        with open(os.path.join("user_data", "config.json"), 'r') as f:
            saved_data = json.load(f)

        self.assertIn("NewSecretApp", saved_data["SENSITIVE_APP_KEYWORDS"])
        self.assertIn("TestSensitive", saved_data["SENSITIVE_APP_KEYWORDS"])

    def test_dictionary_editor_logic(self):
        mock_parent = MockWidget()
        initial_data = {"Key1": "Val1"}
        editor = DictionaryEditor(mock_parent, initial_data)

        self.assertEqual(editor.get_data(), initial_data)

        # Test Add/Update
        editor.key_entry.value = "Key2"
        editor.val_entry.value = "Val2"

        editor.add_update_item()

        self.assertEqual(editor.get_data(), {"Key1": "Val1", "Key2": "Val2"})

        # Test Delete logic
        mock_tree = MagicMock()
        mock_tree.selection.return_value = ("I001",)
        mock_tree.item.return_value = {'values': ["Key1", "Val1"]}
        mock_tree.get_children.return_value = []

        editor.tree = mock_tree

        editor.delete_item()

        self.assertEqual(editor.get_data(), {"Key2": "Val2"})

    def test_list_editor_logic(self):
        mock_parent = MockWidget()
        initial_data = ["Item1", "Item2"]
        editor = ListEditor(mock_parent, initial_data)

        self.assertEqual(editor.get_data(), initial_data)

        # Test Add
        editor.entry = MockEntry()
        editor.entry.value = "Item3"

        editor.add_item()

        self.assertEqual(editor.get_data(), ["Item1", "Item2", "Item3"])

        # Test Delete
        mock_tree = MagicMock()
        mock_tree.selection.return_value = ("I001",)
        mock_tree.item.return_value = {'values': ["Item1"]}
        mock_tree.get_children.return_value = []

        editor.tree = mock_tree

        editor.delete_item()

        self.assertEqual(editor.get_data(), ["Item2", "Item3"])

if __name__ == '__main__':
    unittest.main()
