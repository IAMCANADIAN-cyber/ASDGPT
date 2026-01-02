import unittest
from core.state_engine import StateEngine

class TestStateEngineSmoothing(unittest.TestCase):
    def test_smoothing_implementation(self):
        # Window size is 5.
        engine = StateEngine()

        # Initial: 50

        # Update 1: 90
        # If window=5, history=[50, 50, 50, 50, 90] -> avg = 58
        engine.update({"state_estimation": {"arousal": 90}})
        s1 = engine.get_state()["arousal"]
        print(f"Update 1 (Input 90): {s1}")
        self.assertTrue(s1 < 90, f"State should not jump to 90 immediately, got {s1}")
        self.assertTrue(s1 > 50, f"State should increase from 50, got {s1}")

        # Update 2: 90
        # history=[50, 50, 50, 90, 90] -> avg = 66
        engine.update({"state_estimation": {"arousal": 90}})
        s2 = engine.get_state()["arousal"]
        print(f"Update 2 (Input 90): {s2}")
        self.assertTrue(s2 > s1, f"State should continue to rise, got {s2}")
        self.assertTrue(s2 < 90, f"State should not reach 90 yet, got {s2}")

        # Update 3, 4, 5: 90
        engine.update({"state_estimation": {"arousal": 90}})
        engine.update({"state_estimation": {"arousal": 90}})
        engine.update({"state_estimation": {"arousal": 90}})

        # Now history is [90, 90, 90, 90, 90] -> avg = 90
        s5 = engine.get_state()["arousal"]
        print(f"Update 5 (Input 90): {s5}")
        self.assertAlmostEqual(s5, 90, delta=1, msg=f"State should converge to 90, got {s5}")

if __name__ == '__main__':
    unittest.main()
