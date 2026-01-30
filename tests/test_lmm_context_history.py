import unittest
from unittest.mock import MagicMock, patch
import time
from core.logic_engine import LogicEngine
from core.lmm_interface import LMMInterface
import config

class TestLMMContextHistory(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_lmm_interface = MagicMock()
        self.mock_video_sensor = MagicMock()
        self.mock_audio_sensor = MagicMock()
        self.mock_window_sensor = MagicMock()

        # Setup mocks for LogicEngine dependencies
        self.logic_engine = LogicEngine(
            audio_sensor=self.mock_audio_sensor,
            video_sensor=self.mock_video_sensor,
            window_sensor=self.mock_window_sensor,
            logger=self.mock_logger,
            lmm_interface=self.mock_lmm_interface
        )

    def test_context_history_growth_and_pruning(self):
        """Test that context history grows and is pruned to max size."""
        # Ensure maxlen is 5 as implemented
        self.assertEqual(self.logic_engine.context_history.maxlen, 5)

        # Mock dependencies to return valid data
        self.logic_engine.last_video_frame = MagicMock()
        self.logic_engine.last_audio_chunk = MagicMock() # Ensure not None
        self.logic_engine.last_audio_chunk.tolist.return_value = [0.1]

        # Call _prepare_lmm_data multiple times
        for i in range(10):
             self.logic_engine._prepare_lmm_data(trigger_reason=f"test_{i}")

        # Should be capped at 5
        self.assertEqual(len(self.logic_engine.context_history), 5)

        # Check last item is the most recent
        last_entry = self.logic_engine.context_history[-1]
        self.assertEqual(last_entry["trigger_reason"], "test_9")

    def test_context_history_content(self):
        """Test that history entries contain expected fields."""
        self.logic_engine.last_video_frame = MagicMock()
        self.logic_engine.last_audio_chunk = MagicMock()
        self.logic_engine.last_audio_chunk.tolist.return_value = [0.1]

        self.mock_window_sensor.get_active_window.return_value = "VS Code"
        self.logic_engine.current_mode = "active"

        self.logic_engine._prepare_lmm_data(trigger_reason="test_content")

        entry = self.logic_engine.context_history[-1]
        self.assertEqual(entry["active_window"], "VS Code")
        self.assertEqual(entry["current_mode"], "active")
        self.assertEqual(entry["trigger_reason"], "test_content")
        self.assertIn("timestamp", entry)
        self.assertIn("video_activity", entry)

    @patch('core.lmm_interface.requests.post')
    def test_lmm_interface_includes_history(self, mock_post):
        """Test that LMMInterface formats history into the prompt."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': '{"state_estimation": {"arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50}}'}}]
        }
        mock_post.return_value = mock_response

        lmm = LMMInterface(data_logger=self.mock_logger)

        # Create a user_context with history
        history = [
            {"timestamp": 1000, "active_window": "Window A", "current_mode": "active", "video_activity": 10.0},
            {"timestamp": 1005, "active_window": "Window B", "current_mode": "active", "video_activity": 5.0}
        ]

        user_context = {
            "current_mode": "active",
            "context_history": history,
            "sensor_metrics": {}
        }

        lmm.process_data(user_context=user_context)

        # Verify the prompt sent to requests.post
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        messages = payload['messages']
        user_message_content = messages[1]['content']

        # user_message_content is a list of dicts. Find the text part.
        text_content = ""
        for part in user_message_content:
            if part['type'] == 'text':
                text_content = part['text']
                break

        self.assertIn("Recent Context History (Last 5 updates):", text_content)
        self.assertIn("Window: Window A", text_content)
        self.assertIn("Window: Window B", text_content)

if __name__ == '__main__':
    unittest.main()
