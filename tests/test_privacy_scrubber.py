import pytest
from unittest.mock import MagicMock
import config
from core.logic_engine import LogicEngine

class TestPrivacyScrubber:

    @pytest.fixture
    def engine(self):
        # LogicEngine has side effects (starts threads if not careful), but constructor seems safe
        # It creates StateEngine, STTInterface (mocked whisper), MusicInterface.
        # We can pass mock objects to init to prevent heavy init.
        mock_logger = MagicMock()
        mock_lmm = MagicMock()
        mock_audio = MagicMock()
        mock_video = MagicMock()
        mock_window = MagicMock()

        return LogicEngine(
            audio_sensor=mock_audio,
            video_sensor=mock_video,
            window_sensor=mock_window,
            logger=mock_logger,
            lmm_interface=mock_lmm
        )

    def test_config_integrity(self):
        """Verify config.SENSITIVE_APP_KEYWORDS has no concatenated strings."""
        keywords = config.SENSITIVE_APP_KEYWORDS
        # We know we fixed "Credit CardPassword" and "SettingBank"
        for kw in keywords:
            assert "Password" not in kw or len(kw) < 20, f"Suspicious keyword found: {kw}"
            assert "Bank" not in kw or len(kw) < 20, f"Suspicious keyword found: {kw}"
            assert "Credit CardPassword" not in kw
            assert "SettingBank" not in kw

        # Check for duplicates
        assert len(keywords) == len(set(keywords)), "Duplicate keywords found in config!"

    def test_scrub_window_title_safe(self, engine):
        """Verify safe titles remain unchanged."""
        assert engine._scrub_window_title("Google Chrome") == "Google Chrome"
        assert engine._scrub_window_title("Visual Studio Code") == "Visual Studio Code"
        assert engine._scrub_window_title("Calculator") == "Calculator"

    def test_scrub_window_title_sensitive(self, engine):
        """Verify sensitive titles are redacted."""
        sensitive_examples = [
            "Chase Bank - Login",
            "My Password Vault",
            "Settings", # Matches 'Setting'
            "Incognito Tab",
            "Tor Browser",
            "1Password",
            "Credit Card Statement.pdf"
        ]

        for title in sensitive_examples:
            scrubbed = engine._scrub_window_title(title)
            assert scrubbed == "[REDACTED]", f"Failed to redact: {title}"

    def test_scrub_window_title_case_insensitive(self, engine):
        """Verify case insensitivity."""
        assert engine._scrub_window_title("bank of america") == "[REDACTED]"
        assert engine._scrub_window_title("PASSWORD manager") == "[REDACTED]"

    def test_scrub_window_title_edge_cases(self, engine):
        """Verify edge cases."""
        assert engine._scrub_window_title(None) is None
        assert engine._scrub_window_title("") == ""

    def test_logic_engine_update_scrubs_history(self, engine):
        """Verify LogicEngine.update() stores redacted title in history."""
        # Setup mock return
        engine.window_sensor.get_active_window.return_value = "Chase Bank - Login"

        # Ensure update runs logic
        engine.current_mode = "active"
        engine.last_history_sample_time = 0 # Force sample

        engine.update()

        assert len(engine.context_history) > 0
        snapshot = engine.context_history[-1]
        assert snapshot["active_window"] == "[REDACTED]"

    def test_prepare_lmm_data_scrubs_active_window(self, engine):
        """Verify _prepare_lmm_data() returns redacted active_window."""
        engine.window_sensor.get_active_window.return_value = "Secret Project - 1Password"

        # Mock sensors to return something so data is prepared
        engine.last_video_frame = MagicMock()
        engine.last_audio_chunk = MagicMock()

        payload = engine._prepare_lmm_data()

        assert payload is not None
        user_context = payload["user_context"]
        assert user_context["active_window"] == "[REDACTED]"

    def test_reflex_logging_is_safe(self, engine, monkeypatch):
        """Verify _check_window_reflexes logs safely."""
        # Mock config to force a match
        monkeypatch.setattr(config, 'REFLEXIVE_WINDOW_TRIGGERS', {"Bank": "alert"})

        # Use raw sensitive title
        title = "Chase Bank"

        # Invoke
        result = engine._check_window_reflexes(title)

        assert result == "alert"

        # Check logs
        engine.logger.log_info.assert_called()
        # Iterate calls to find the reflex match log
        found_log = False
        for call in engine.logger.log_info.call_args_list:
            args = call[0]
            if "Reflexive Window Match" in args[0]:
                found_log = True
                assert "Chase Bank" not in args[0]
                assert "active window" in args[0]

        assert found_log, "Did not find Reflexive Window Match log"
