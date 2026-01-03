import numpy as np
import scipy.io.wavfile as wavfile
from PIL import Image, ImageDraw
import os

def generate_tone(filepath, frequency=440, duration=1.0, samplerate=44100):
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    # Generate a sine wave
    data = 0.5 * np.sin(2 * np.pi * frequency * t)
    # Convert to 16-bit integer PCM
    scaled_data = np.int16(data * 32767)
    wavfile.write(filepath, samplerate, scaled_data)
    print(f"Generated tone at {filepath}")

def generate_image(filepath, size=(200, 200), color='blue'):
    img = Image.new('RGB', size, color=color)
    d = ImageDraw.Draw(img)
    d.text((10, 10), "Test Image", fill='white')
    img.save(filepath)
    print(f"Generated image at {filepath}")

if __name__ == "__main__":
    assets_dir = "assets"
    sounds_dir = os.path.join(assets_dir, "sounds")
    images_dir = os.path.join(assets_dir, "images")

    os.makedirs(sounds_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)

    generate_tone(os.path.join(sounds_dir, "test_tone.wav"))
    generate_image(os.path.join(images_dir, "test_image.png"))

    # Also generate the files referenced in config.py for seamless testing
    generate_tone(os.path.join(sounds_dir, "calming_waves.wav"), frequency=220) # Lower tone
    generate_tone(os.path.join(sounds_dir, "urgent_alert_tone.wav"), frequency=880, duration=0.5) # Higher, shorter tone
