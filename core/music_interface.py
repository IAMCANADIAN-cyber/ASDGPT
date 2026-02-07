import os
import platform
import subprocess
import threading
import json
import random
from typing import Optional, Dict, Any, List

# Try importing pyautogui for cross-platform control
try:
    import pyautogui
except ImportError:
    pyautogui = None

class MusicInterface:
    """
    Handles music playback control based on mood/arousal.
    Controls:
    - System Media Keys (via pyautogui)
    - Spotify CLI (spotify-cli-linux or similar) - Placeholder logic
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.current_playlist = None
        self._lock = threading.Lock()

        # Mapping of (Mood, Arousal) -> Playlist URI or Keyword
        # This could be moved to config.py
        self.mood_playlists = {
            "high_arousal_positive": "spotify:playlist:workout_pump",
            "low_arousal_positive": "spotify:playlist:chill_vibes",
            "high_arousal_negative": "spotify:playlist:stress_relief",
            "low_arousal_negative": "spotify:playlist:comfort_zone",
            "erotic": "spotify:playlist:sultry_mix"
        }

    def _log_info(self, msg: str) -> None:
        if self.logger:
            self.logger.log_info(f"MusicInterface: {msg}")
        else:
            print(f"MusicInterface: {msg}")

    def play_pause(self) -> None:
        """Toggles play/pause."""
        self._log_info("Toggling Play/Pause")
        if pyautogui:
            pyautogui.press('playpause')
        else:
            self._system_media_key("playpause")

    def next_track(self) -> None:
        """Skips to next track."""
        self._log_info("Next Track")
        if pyautogui:
            pyautogui.press('nexttrack')
        else:
            self._system_media_key("next")

    def previous_track(self) -> None:
        """Skips to previous track."""
        self._log_info("Previous Track")
        if pyautogui:
            pyautogui.press('prevtrack')
        else:
            self._system_media_key("prev")

    def _system_media_key(self, key: str) -> None:
        """Fallback for media keys using xdotool (Linux) or similar."""
        if platform.system() == "Linux":
            try:
                # Requires xdotool
                map_keys = {
                    "playpause": "XF86AudioPlay",
                    "next": "XF86AudioNext",
                    "prev": "XF86AudioPrev"
                }
                cmd = f"xdotool key {map_keys.get(key, '')}"
                subprocess.Popen(cmd, shell=True)
            except:
                pass

    def play_mood_playlist(self, mood: int, arousal: int, sexual_arousal: int = 0) -> None:
        """
        Selects and plays a playlist based on state.
        This usually requires a specific integration (e.g., Spotify API or CLI).
        Here we emulate the logic and log the intended action.
        """
        category = "low_arousal_positive" # Default

        if sexual_arousal > 50:
            category = "erotic"
        elif arousal > 60:
            if mood > 50:
                category = "high_arousal_positive"
            else:
                category = "high_arousal_negative"
        else:
            if mood > 50:
                category = "low_arousal_positive"
            else:
                category = "low_arousal_negative"

        uri = self.mood_playlists.get(category)

        if uri != self.current_playlist:
            self._log_info(f"Changing mood music to: {category} ({uri})")
            self.current_playlist = uri
            self._trigger_spotify_playback(uri)

    def _trigger_spotify_playback(self, uri: str) -> None:
        """
        Triggers playback of a specific URI.
        Requires 'spotify' (Linux) or 'open' (Mac) to handle URI.
        """
        try:
            if platform.system() == "Linux":
                # Try calling spotify directly if installed
                subprocess.Popen(["spotify", "--uri", uri], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            elif platform.system() == "Darwin":
                # MacOS open command handles spotify: URIs
                subprocess.Popen(["open", uri])
            elif platform.system() == "Windows":
                # Windows start command
                os.system(f'start {uri}')
        except Exception as e:
            self._log_info(f"Failed to trigger Spotify playback: {e}")
