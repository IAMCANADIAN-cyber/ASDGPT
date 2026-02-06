import unittest
from unittest.mock import MagicMock, patch
from core.lmm_interface import LMMInterface
from core.logic_engine import LogicEngine
import config

class TestContextIntelligence(unittest.TestCase):

    def test_lmm_truncation(self):
        """Verify LMMInterface truncates long strings."""
        lmm = LMMInterface()

        short_text = "Hello World"
        long_text = "A" * 150

        self.assertEqual(lmm._truncate_text(short_text, 100), short_text)
        self.assertEqual(len(lmm._truncate_text(long_text, 100)), 100)
        self.assertTrue(lmm._truncate_text(long_text, 100).endswith("..."))

        # Test boundary
        exact_text = "B" * 100
        self.assertEqual(lmm._truncate_text(exact_text, 100), exact_text)

    def test_rapid_task_switching(self):
        """Verify LogicEngine detects rapid task switching."""
        engine = LogicEngine()

        # Helper to add snapshot
        def add_snap(win):
            engine.context_history.append({'active_window': win})

        # Case 1: Low Switching (A, A, A, A, A)
        add_snap("App A")
        add_snap("App A")
        add_snap("App A")
        add_snap("App A")
        add_snap("App A")
        self.assertFalse(engine._detect_rapid_task_switching())

        # Case 2: Moderate Switching (A, B, A, B, A) -> 2 unique
        engine.context_history.clear()
        add_snap("App A")
        add_snap("App B")
        add_snap("App A")
        add_snap("App B")
        add_snap("App A")
        self.assertFalse(engine._detect_rapid_task_switching())

        # Case 3: High Switching (A, B, C, D, E) -> 5 unique
        engine.context_history.clear()
        add_snap("App A")
        add_snap("App B")
        add_snap("App C")
        add_snap("App D")
        add_snap("App E")
        self.assertTrue(engine._detect_rapid_task_switching())

        # Case 4: High Switching (A, B, C, D, A) -> 4 unique
        engine.context_history.clear()
        add_snap("App A")
        add_snap("App B")
        add_snap("App C")
        add_snap("App D")
        add_snap("App A")
        self.assertTrue(engine._detect_rapid_task_switching())

        # Case 5: Ignore Unknown
        engine.context_history.clear()
        add_snap("App A")
        add_snap("Unknown")
        add_snap("App B")
        add_snap("Unknown")
        add_snap("App C")
        # Unique: A, B, C -> 3. Should be False.
        self.assertFalse(engine._detect_rapid_task_switching())

    def test_system_alert_injection(self):
        """Verify the alert is actually injected into the context."""
        engine = LogicEngine()

        # Mock history to trigger switching
        engine.context_history.append({'active_window': "App A"})
        engine.context_history.append({'active_window': "App B"})
        engine.context_history.append({'active_window': "App C"})
        engine.context_history.append({'active_window': "App D"})

        # Mock dependencies
        # We set last_video_frame to something not None to bypass the initial check
        engine.last_video_frame = MagicMock()

        # Mock cv2 to avoid actual encoding
        with patch('cv2.imencode') as mock_encode:
             mock_encode.return_value = (True, b'fake_data')
             # Also mock base64 to avoid decoding bytes
             with patch('base64.b64encode', return_value=b'encoded'):
                 data = engine._prepare_lmm_data()

                 self.assertIsNotNone(data)
                 user_context = data['user_context']
                 alerts = user_context.get('system_alerts', [])
                 self.assertIn("High Rate of Task Switching Detected", alerts)

if __name__ == '__main__':
    unittest.main()
