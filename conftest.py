import sys
import pytest
from unittest.mock import MagicMock

# Mock sounddevice
sys.modules["sounddevice"] = MagicMock()
sys.modules["sounddevice"].query_devices.return_value = []

# Mock pystray and PIL
sys.modules["pystray"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["PIL.ImageDraw"] = MagicMock()

# Add project root to sys.path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
