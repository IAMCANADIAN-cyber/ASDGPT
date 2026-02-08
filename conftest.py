import sys
import pytest
from unittest.mock import MagicMock
import os

# Mock sounddevice
sys.modules["sounddevice"] = MagicMock()
sys.modules["sounddevice"].query_devices.return_value = []

# Mock pystray and PIL
sys.modules["pystray"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["PIL.ImageDraw"] = MagicMock()

# Mock pyautogui and mouseinfo for headless environment to prevent DISPLAY errors
sys.modules["pyautogui"] = MagicMock()
sys.modules["mouseinfo"] = MagicMock()

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
