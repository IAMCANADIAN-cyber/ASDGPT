
import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
import json
import config

from core.social_media_manager import SocialMediaManager
# Mock pyautogui to prevent Xlib errors in headless env
import sys
sys.modules['pyautogui'] = MagicMock()
from core.music_interface import MusicInterface

class TestSocialMedia(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/test_drafts"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

        self.manager = SocialMediaManager(logger=MagicMock())
        self.manager.drafts_dir = self.test_dir

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_create_draft(self):
        # Create a dummy image
        img_path = os.path.join(self.test_dir, "test.jpg")
        with open(img_path, 'w') as f:
            f.write("dummy image content")

        draft_path = self.manager.create_draft(img_path, context="erotic pose")
        self.assertIsNotNone(draft_path)

        # Check platform folder
        platform_dir = os.path.join(self.test_dir, "instagram")
        self.assertTrue(os.path.exists(platform_dir))

        # Check json metadata
        json_path = draft_path + ".json"
        self.assertTrue(os.path.exists(json_path))

        with open(json_path, 'r') as f:
            data = json.load(f)
            self.assertIn("#mood", data["caption"]) # Checks context logic

class TestMusicControl(unittest.TestCase):
    def test_music_logic(self):
        mi = MusicInterface(logger=MagicMock())

        # Mock playback trigger
        mi._trigger_spotify_playback = MagicMock()

        # Test High Arousal / High Mood -> Workout
        mi.play_mood_playlist(mood=80, arousal=80)
        mi._trigger_spotify_playback.assert_called_with("spotify:playlist:workout_pump")

        # Test Erotic
        mi.play_mood_playlist(mood=50, arousal=50, sexual_arousal=80)
        mi._trigger_spotify_playback.assert_called_with("spotify:playlist:sultry_mix")

if __name__ == '__main__':
    unittest.main()
