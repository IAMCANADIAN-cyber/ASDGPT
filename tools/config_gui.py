import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys

# Ensure we can import config relative to this script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

class ListEditor(ttk.Frame):
    def __init__(self, parent, data=None):
        super().__init__(parent)
        self.data = data.copy() if data else []
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        # Treeview for List Items
        columns = ('Item',)
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        self.tree.heading('Item', text='Keyword / Pattern')
        self.tree.pack(fill='both', expand=True, padx=5, pady=5)

        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # Edit Frame
        edit_frame = ttk.Frame(self)
        edit_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(edit_frame, text="Value:").pack(side='left')
        self.entry = ttk.Entry(edit_frame)
        self.entry.pack(side='left', fill='x', expand=True, padx=5)

        ttk.Button(edit_frame, text="Add", command=self.add_item).pack(side='left', padx=5)
        ttk.Button(edit_frame, text="Delete Selected", command=self.delete_item).pack(side='left', padx=5)

    def refresh_list(self):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Populate
        for item in self.data:
            self.tree.insert('', 'end', values=(item,))

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            val = self.tree.item(item_id)['values'][0]
            self.entry.delete(0, 'end')
            self.entry.insert(0, val)

    def add_item(self):
        val = self.entry.get().strip()
        if val:
            if val not in self.data:
                self.data.append(val)
                self.refresh_list()
            # Clear entry
            self.entry.delete(0, 'end')

    def delete_item(self):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            val = self.tree.item(item_id)['values'][0]
            if val in self.data:
                self.data.remove(val)
                self.refresh_list()

    def get_data(self):
        return self.data

class DictionaryEditor(ttk.Frame):
    def __init__(self, parent, data=None):
        super().__init__(parent)
        self.data = data.copy() if data else {}
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        # Treeview for Key-Value pairs
        columns = ('Key', 'Value')
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        self.tree.heading('Key', text='Window Keyword')
        self.tree.heading('Value', text='Intervention ID')
        self.tree.pack(fill='both', expand=True, padx=5, pady=5)

        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # Edit Frame
        edit_frame = ttk.Frame(self)
        edit_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(edit_frame, text="Keyword:").pack(side='left')
        self.key_entry = ttk.Entry(edit_frame)
        self.key_entry.pack(side='left', fill='x', expand=True, padx=5)

        ttk.Label(edit_frame, text="Intervention:").pack(side='left')
        self.val_entry = ttk.Entry(edit_frame)
        self.val_entry.pack(side='left', fill='x', expand=True, padx=5)

        ttk.Button(edit_frame, text="Add/Update", command=self.add_update_item).pack(side='left', padx=5)
        ttk.Button(edit_frame, text="Delete Selected", command=self.delete_item).pack(side='left', padx=5)

    def refresh_list(self):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Populate
        for key, val in self.data.items():
            self.tree.insert('', 'end', values=(key, val))

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            key, val = item['values']
            self.key_entry.delete(0, 'end')
            self.key_entry.insert(0, key)
            self.val_entry.delete(0, 'end')
            self.val_entry.insert(0, val)

    def add_update_item(self):
        key = self.key_entry.get().strip()
        val = self.val_entry.get().strip()
        if key and val:
            self.data[key] = val
            self.refresh_list()
            # Clear entries
            self.key_entry.delete(0, 'end')
            self.val_entry.delete(0, 'end')
        else:
            messagebox.showwarning("Input Error", "Both Keyword and Intervention ID are required.")

    def delete_item(self):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            key = item['values'][0]
            if key in self.data:
                del self.data[key]
                self.refresh_list()

    def get_data(self):
        return self.data

class ConfigGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ACR Configuration")
        self.root.geometry("800x600")

        self.config_data = {}
        self.load_current_config()

        self.create_widgets()

    def load_current_config(self):
        """Loads current user config from disk or defaults."""
        config_path = os.path.join("user_data", "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.config_data = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config_data = {}
        else:
            self.config_data = {}

    def get_val(self, key, default):
        # Helper to get from user config or fallback to config.py
        if key in self.config_data:
            return self.config_data[key]
        return getattr(config, key, default)

    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # --- Tab 1: General & Thresholds ---
        tab_general = ttk.Frame(notebook)
        notebook.add(tab_general, text='General')

        self.entries = {}

        row = 0
        ttk.Label(tab_general, text="Audio Threshold (High):").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.entries['AUDIO_THRESHOLD_HIGH'] = ttk.Entry(tab_general)
        self.entries['AUDIO_THRESHOLD_HIGH'].insert(0, str(self.get_val('AUDIO_THRESHOLD_HIGH', 0.5)))
        self.entries['AUDIO_THRESHOLD_HIGH'].grid(row=row, column=1, sticky='ew', padx=5)

        row += 1
        ttk.Label(tab_general, text="Video Activity Threshold:").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.entries['VIDEO_ACTIVITY_THRESHOLD_HIGH'] = ttk.Entry(tab_general)
        self.entries['VIDEO_ACTIVITY_THRESHOLD_HIGH'].insert(0, str(self.get_val('VIDEO_ACTIVITY_THRESHOLD_HIGH', 20.0)))
        self.entries['VIDEO_ACTIVITY_THRESHOLD_HIGH'].grid(row=row, column=1, sticky='ew', padx=5)

        row += 1
        ttk.Label(tab_general, text="Sexual Arousal Threshold:").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.entries['SEXUAL_AROUSAL_THRESHOLD'] = ttk.Entry(tab_general)
        self.entries['SEXUAL_AROUSAL_THRESHOLD'].insert(0, str(self.get_val('SEXUAL_AROUSAL_THRESHOLD', 50)))
        self.entries['SEXUAL_AROUSAL_THRESHOLD'].grid(row=row, column=1, sticky='ew', padx=5)

        # --- Tab 2: Paths & Output ---
        tab_paths = ttk.Frame(notebook)
        notebook.add(tab_paths, text='Paths')

        row = 0
        ttk.Label(tab_paths, text="Erotic Content Dir:").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.entries['EROTIC_CONTENT_OUTPUT_DIR'] = ttk.Entry(tab_paths)
        self.entries['EROTIC_CONTENT_OUTPUT_DIR'].insert(0, str(self.get_val('EROTIC_CONTENT_OUTPUT_DIR', 'captures/erotic')))
        self.entries['EROTIC_CONTENT_OUTPUT_DIR'].grid(row=row, column=1, sticky='ew', padx=5)

        # --- Tab 3: Voice & Model ---
        tab_voice = ttk.Frame(notebook)
        notebook.add(tab_voice, text='Voice')

        row = 0
        ttk.Label(tab_voice, text="TTS Engine (system/coqui):").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.entries['TTS_ENGINE'] = ttk.Combobox(tab_voice, values=['system', 'coqui'])
        self.entries['TTS_ENGINE'].set(str(self.get_val('TTS_ENGINE', 'system')))
        self.entries['TTS_ENGINE'].grid(row=row, column=1, sticky='ew', padx=5)

        row += 1
        ttk.Label(tab_voice, text="TTS Voice ID (System):").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.entries['TTS_VOICE_ID'] = ttk.Entry(tab_voice)
        val = self.get_val('TTS_VOICE_ID', '')
        if val: self.entries['TTS_VOICE_ID'].insert(0, str(val))
        self.entries['TTS_VOICE_ID'].grid(row=row, column=1, sticky='ew', padx=5)

        row += 1
        ttk.Label(tab_voice, text="Voice Clone Source (WAV path):").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.entries['TTS_VOICE_CLONE_SOURCE'] = ttk.Entry(tab_voice)
        val = self.get_val('TTS_VOICE_CLONE_SOURCE', '')
        if val: self.entries['TTS_VOICE_CLONE_SOURCE'].insert(0, str(val))
        self.entries['TTS_VOICE_CLONE_SOURCE'].grid(row=row, column=1, sticky='ew', padx=5)

        # --- Tab 4: Focus & Distraction (New) ---
        tab_lists = ttk.Frame(notebook)
        notebook.add(tab_lists, text='Focus & Distraction')

        # Split into two panes
        paned_window = ttk.PanedWindow(tab_lists, orient=tk.HORIZONTAL)
        paned_window.pack(fill='both', expand=True, padx=5, pady=5)

        # Distraction Pane
        distraction_frame = ttk.Labelframe(paned_window, text="Distraction Apps (Triggers Alerts)")
        paned_window.add(distraction_frame, weight=1)

        distraction_data = self.get_val('DISTRACTION_APPS', [])
        if not isinstance(distraction_data, list): distraction_data = []
        self.distraction_editor = ListEditor(distraction_frame, data=distraction_data)
        self.distraction_editor.pack(fill='both', expand=True)

        # Focus Pane
        focus_frame = ttk.Labelframe(paned_window, text="Focus Apps (Safe List)")
        paned_window.add(focus_frame, weight=1)

        focus_data = self.get_val('FOCUS_APPS', [])
        if not isinstance(focus_data, list): focus_data = []
        self.focus_editor = ListEditor(focus_frame, data=focus_data)
        self.focus_editor.pack(fill='both', expand=True)

        # --- Tab 5: Advanced Triggers ---
        tab_triggers = ttk.Frame(notebook)
        notebook.add(tab_triggers, text='Advanced Triggers')

        # Helper text
        ttk.Label(tab_triggers, text="Define custom window titles that trigger specific interventions.").pack(anchor='w', padx=5, pady=5)

        triggers_data = self.get_val('REFLEXIVE_WINDOW_TRIGGERS', {})
        self.triggers_editor = DictionaryEditor(tab_triggers, data=triggers_data)
        self.triggers_editor.pack(fill='both', expand=True)

        # --- Tab 6: Privacy ---
        tab_privacy = ttk.Frame(notebook)
        notebook.add(tab_privacy, text='Privacy')

        ttk.Label(tab_privacy, text="Sensitive Apps & Keywords (Redacted from History):").pack(anchor='w', padx=5, pady=5)

        privacy_data = self.get_val('SENSITIVE_APP_KEYWORDS', [])
        # Ensure it's a list (handle potential conflicts if config has it as something else)
        if not isinstance(privacy_data, list):
            privacy_data = []

        self.privacy_editor = ListEditor(tab_privacy, data=privacy_data)
        self.privacy_editor.pack(fill='both', expand=True)


        # Save Button
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill='x', padx=10, pady=10)
        ttk.Button(btn_frame, text="Save Configuration", command=self.save_config).pack(side='right')

    def save_config(self):
        new_config = {}
        try:
            # Parse values
            for key, widget in self.entries.items():
                val = widget.get()
                # Simple type inference (string to float/int if possible)
                if key.endswith("THRESHOLD") or key.endswith("THRESHOLD_HIGH"):
                    try:
                        val = float(val) if "." in val else int(val)
                    except ValueError:
                        pass # Keep as string if conversion fails
                new_config[key] = val

            # Get Focus/Distraction Data
            new_config['DISTRACTION_APPS'] = self.distraction_editor.get_data()
            new_config['FOCUS_APPS'] = self.focus_editor.get_data()

            # Get Triggers Data
            new_config['REFLEXIVE_WINDOW_TRIGGERS'] = self.triggers_editor.get_data()

            # Get Privacy Data
            new_config['SENSITIVE_APP_KEYWORDS'] = self.privacy_editor.get_data()

            # Merge with existing
            self.config_data.update(new_config)

            # Save
            os.makedirs("user_data", exist_ok=True)
            with open(os.path.join("user_data", "config.json"), 'w') as f:
                json.dump(self.config_data, f, indent=4)

            messagebox.showinfo("Success", "Configuration saved! Restart the application to apply changes.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigGUI(root)
    root.mainloop()
