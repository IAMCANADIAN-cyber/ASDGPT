import unittest
import sys
import os
import shutil
import time
import numpy as np
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.replay_harness import ReplayHarness
from core.intervention_engine import InterventionEngine
from core.logic_engine import LogicEngine
import config

class TestNewModes(unittest.TestCase):
    def setUp(self):
        # Ensure captures directory exists (and clean it up if needed)
        self.captures_dir = "captures"
        if not os.path.exists(self.captures_dir):
            os.makedirs(self.captures_dir)

    def tearDown(self):
        # Optional: cleanup captures
        pass

    def test_content_creation_trigger(self):
        """
        Verifies that 'Content Creation' context triggers 'content_pivot'.
        """
        scenario = [
            {
                "description": "Step 1: High Energy + Camera Interaction -> Content Pivot",
                "input": {
                    "audio_level": 0.3,
                    "video_activity": 25.0 # High activity
                },
                "input_analysis": {
                    "audio": {"rms": 0.3, "pitch_variance": 60, "speech_rate": 4.5}, # High energy
                    "video": {"face_detected": True, "face_size_ratio": 0.2}
                },
                "expected_outcome": {
                    "visual_context": ["camera_interaction", "studio_lighting"],
                    "state_estimation": {"energy": 80, "mood": 80},
                    "intervention": "content_pivot"
                }
            }
        ]

        harness = ReplayHarness()
        results = harness.run_scenario(scenario)
        harness.print_report(results)

        self.assertTrue(results['step_results'][0]['success'], "Content Creation trigger failed")

    def test_intimacy_trigger(self):
        """
        Verifies that 'Intimacy' context triggers 'sultry_persona_prompt'.
        """
        scenario = [
            {
                "description": "Step 1: Low Speech Rate + Lying Down -> Sultry Persona",
                "input": {
                    "audio_level": 0.1,
                    "video_activity": 2.0 # Low activity
                },
                "input_analysis": {
                    "audio": {"rms": 0.1, "pitch_variance": 5, "speech_rate": 1.5}, # Low energy/rate
                    "video": {"face_detected": True}
                },
                "expected_outcome": {
                    "visual_context": ["lying_down", "low_light"],
                    "state_estimation": {"energy": 20, "arousal": 60},
                    "intervention": "sultry_persona_prompt"
                }
            }
        ]

        harness = ReplayHarness()
        results = harness.run_scenario(scenario)
        harness.print_report(results)

        self.assertTrue(results['step_results'][0]['success'], "Intimacy trigger failed")

    def test_capture_image_execution(self):
        """
        Verifies that InterventionEngine._capture_image actually saves a file.
        """
        # Mock LogicEngine and App
        mock_logic = MagicMock(spec=LogicEngine)
        # Create a dummy frame
        dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Add some color to distinguish
        dummy_frame[:] = (0, 0, 255) # Red
        mock_logic.last_video_frame = dummy_frame
        mock_logic.get_mode.return_value = "active"

        mock_app = MagicMock()
        mock_app.data_logger = MagicMock()

        # Instantiate real InterventionEngine
        engine = InterventionEngine(mock_logic, mock_app)

        # Call _capture_image directly
        test_details = "unit_test_capture"

        # We need to wait a bit or just verify file existence immediately?
        # It's synchronous in _capture_image using cv2.imwrite

        with patch('cv2.imwrite') as mock_imwrite:
            engine._capture_image(test_details)

            # Verify cv2.imwrite was called
            self.assertTrue(mock_imwrite.called)
            args, _ = mock_imwrite.call_args
            filename = args[0]
            frame = args[1]

            self.assertIn("captures/capture_", filename)
            self.assertIn(test_details, filename)
            self.assertTrue(np.array_equal(frame, dummy_frame))

            print(f"\nVerified capture called with filename: {filename}")

if __name__ == '__main__':
    unittest.main()
