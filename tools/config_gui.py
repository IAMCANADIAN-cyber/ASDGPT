import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys

# Ensure we can import config relative to this script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

class ConfigGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ACR Configuration")
        self.root.geometry("600x500")

        self.config_data = {}
        self.load_current_config()

        self.create_widgets()

    def load_current_config(self):
        """Loads current user config from disk or defaults."""
        config_path = os.path.join("user_data", "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config_data = json.load(f)
        else:
            self.config_data = {}

    def get_val(self, key, default):
        return self.config_data.get(key, getattr(config, key, default))

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
                # Simple type inference
                if key.endswith("THRESHOLD") or key.endswith("THRESHOLD_HIGH"):
                    val = float(val) if "." in val else int(val)
                new_config[key] = val

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
