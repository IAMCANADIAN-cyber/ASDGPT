import time
import os
import unittest
import config

try:
    import numpy as np
    import scipy.io.wavfile as wav
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

from core.intervention_engine import InterventionEngine

class MockApp:
    def __init__(self):
        self.data_logger = MockLogger()
        self.tray_icon = MockTrayIcon()

class MockLogger:
    def log_info(self, msg): print(f"INFO: {msg}")
    def log_debug(self, msg): print(f"DEBUG: {msg}")
    def log_warning(self, msg): print(f"WARN: {msg}")
    def log_error(self, msg, details=""): print(f"ERROR: {msg} {details}")
    def log_event(self, *args, **kwargs): pass

class MockTrayIcon:
    def flash_icon(self, *args, **kwargs): pass

class MockLogicEngine:
    def get_mode(self): return "active"

class TestSoundPlayback(unittest.TestCase):

    @unittest.skipUnless(DEPENDENCIES_AVAILABLE, "Numpy or Scipy not available")
    def test_playback(self):
        print("Generating test tone...")
        filename = "test_tone.wav"

        # Generate dummy wav
        sample_rate = 44100
        duration = 0.5
        frequency = 440.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(frequency * t * 2 * np.pi)
        audio = (tone * 32767).astype(np.int16)
        wav.write(filename, sample_rate, audio)

        app = MockApp()
        logic = MockLogicEngine()
        engine = InterventionEngine(logic, app)

        print("Testing playback...")
        try:
            # We expect this to either work or log an error (if no audio device),
            # but NOT raise an exception that crashes the app.
            # InterventionEngine catches exceptions internally.
            engine._play_sound(filename)
            print("Playback call completed.")
        except Exception as e:
            self.fail(f"Playback raised exception: {e}")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

if __name__ == "__main__":
    if not hasattr(config, 'FEEDBACK_WINDOW_SECONDS'): config.FEEDBACK_WINDOW_SECONDS = 15
    if not hasattr(config, 'MIN_TIME_BETWEEN_INTERVENTIONS'): config.MIN_TIME_BETWEEN_INTERVENTIONS = 0
    unittest.main()
