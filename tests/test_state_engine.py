import unittest
from core.state_engine import StateEngine
from unittest.mock import MagicMock

class TestStateEngine(unittest.TestCase):
    def test_initialization(self):
        engine = StateEngine()
        state = engine.get_state()
        self.assertEqual(state['arousal'], 50)
        self.assertEqual(state['overload'], 0)
        self.assertEqual(state['focus'], 50)
        self.assertEqual(state['energy'], 80)
        self.assertEqual(state['mood'], 50)
        self.assertEqual(engine.history_size, 5)

    def test_update_valid_state(self):
        engine = StateEngine(history_size=1)
        new_state = {
            "state_estimation": {
                "arousal": 60,
                "overload": 10,
                "focus": 80,
                "energy": 70,
                "mood": 60
            }
        }
        engine.update(new_state)
        state = engine.get_state()
        self.assertEqual(state['arousal'], 60)
        self.assertEqual(state['overload'], 10)
        self.assertEqual(state['focus'], 80)

    def test_update_partial_state(self):
        engine = StateEngine(history_size=1)
        new_state = {
            "state_estimation": {
                "arousal": 70
            }
        }
        engine.update(new_state)
        state = engine.get_state()
        self.assertEqual(state['arousal'], 70)
        self.assertEqual(state['focus'], 50) # Should remain unchanged

    def test_update_invalid_values(self):
        mock_logger = MagicMock()
        engine = StateEngine(logger=mock_logger, history_size=1)

        # Test out of bounds
        engine.update({"state_estimation": {"arousal": 150}})
        self.assertEqual(engine.get_state()['arousal'], 100) # Clamped

        engine.update({"state_estimation": {"arousal": -50}})
        self.assertEqual(engine.get_state()['arousal'], 0) # Clamped

        # Test non-numeric
        engine.update({"state_estimation": {"arousal": "not_a_number"}})
        # Should log warning and keep previous value
        mock_logger.log_warning.assert_called()
        self.assertEqual(engine.get_state()['arousal'], 0) # Last valid value was 0

    def test_smoothing(self):
        engine = StateEngine(history_size=3)
        # Initial is 50. History: [50, 50, 50]

        # Add 80. History: [50, 50, 80] -> Avg 60
        engine.update({"state_estimation": {"arousal": 80}})
        self.assertEqual(engine.get_state()['arousal'], 60)

        # Add 80. History: [50, 80, 80] -> Avg 70
        engine.update({"state_estimation": {"arousal": 80}})
        self.assertEqual(engine.get_state()['arousal'], 70)

        # Add 80. History: [80, 80, 80] -> Avg 80
        engine.update({"state_estimation": {"arousal": 80}})
        self.assertEqual(engine.get_state()['arousal'], 80)

if __name__ == '__main__':
    unittest.main()
