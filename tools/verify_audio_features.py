import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sensors.audio_sensor import AudioSensor

class MockLogger:
    def log_info(self, msg): print(f"INFO: {msg}")
    def log_warning(self, msg): print(f"WARN: {msg}")
    def log_error(self, msg, details=""): print(f"ERROR: {msg} {details}")

def generate_sine_wave(freq, duration, sample_rate=44100, amplitude=0.5):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq * t)

def test_pitch_variance_step():
    logger = MockLogger()
    sensor = AudioSensor(data_logger=logger, chunk_duration=0.1, history_seconds=2.0)

    print("\n--- Testing Monotone (Sine Wave 440Hz) ---")
    monotone = generate_sine_wave(440, 2.0)
    chunk_size = sensor.chunk_size

    for i in range(0, len(monotone), chunk_size):
        chunk = monotone[i:i+chunk_size]
        if len(chunk) < chunk_size: break
        m = sensor.analyze_chunk(chunk)

    print(f"Final Pitch Variance: {m['pitch_variance']:.2f}")

    print("\n--- Testing Step Change (440Hz -> 600Hz) ---")
    sensor = AudioSensor(data_logger=logger, chunk_duration=0.1, history_seconds=2.0)

    part1 = generate_sine_wave(440, 1.0)
    part2 = generate_sine_wave(600, 1.0)
    expressive = np.concatenate((part1, part2))

    pitches = []
    for i in range(0, len(expressive), chunk_size):
        chunk = expressive[i:i+chunk_size]
        if len(chunk) < chunk_size: break
        m = sensor.analyze_chunk(chunk)
        pitches.append(m['pitch_estimation'])

    print(f"Pitches: {pitches}")
    print(f"Final Pitch Variance: {m['pitch_variance']:.2f}")

    if m['pitch_variance'] > 10.0:
        print("PASS: High variance for step signal.")
    else:
        print("FAIL: Low variance for step signal.")

if __name__ == "__main__":
    test_pitch_variance_step()
