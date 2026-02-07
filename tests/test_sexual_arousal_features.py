
import unittest
import os
import shutil
import time
from unittest.mock import MagicMock, patch
import cv2
import numpy as np

import config
from core.state_engine import StateEngine
from core.intervention_engine import InterventionEngine
from core.lmm_interface import LMMInterface
from core.logic_engine import LogicEngine

class TestSexualArousalFeatures(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.output_dir = "tests/test_erotic_output"
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir)

        # Patch Config
        self.config_patcher = patch.dict(config.__dict__, {
            'EROTIC_CONTENT_OUTPUT_DIR': self.output_dir,
            'SEXUAL_AROUSAL_THRESHOLD': 50
        })
        self.config_patcher.start()

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        self.config_patcher.stop()

    def test_state_engine_sexual_arousal(self):
        """Verify StateEngine tracks sexual_arousal correctly."""
        engine = StateEngine(logger=self.mock_logger)
        initial_state = engine.get_state()
        self.assertIn("sexual_arousal", initial_state)
        self.assertEqual(initial_state["sexual_arousal"], 0)

        # Update with high arousal
        analysis = {
            "state_estimation": {
                "arousal": 50, "overload": 0, "focus": 50, "energy": 50, "mood": 50,
                "sexual_arousal": 80
            }
        }
        engine.update(analysis)
        new_state = engine.get_state()
        # Since history starts with 0s, smoothed value will be low but > 0
        self.assertGreater(new_state["sexual_arousal"], 0)

    def test_intervention_routing(self):
        """Verify erotic interventions save to the correct directory."""
        # Setup LogicEngine with a mock frame
        logic_engine = MagicMock()
        logic_engine.last_video_frame = np.zeros((100, 100, 3), dtype=np.uint8)

        intervention_engine = InterventionEngine(logic_engine=logic_engine, app_instance=MagicMock())
        intervention_engine.app.data_logger = self.mock_logger

        # Trigger capture with keyword
        intervention_engine._capture_image("erotic_pose_suggestion")

        # Verify file creation in output dir
        files = os.listdir(self.output_dir)
        self.assertTrue(len(files) > 0, "Should have saved an image to the erotic output directory.")
        self.assertTrue(files[0].endswith(".jpg"))

    def test_logic_engine_acceleration(self):
        """Verify LogicEngine triggers accelerated checks on high sexual arousal."""
        lmm_interface = MagicMock()
        logic_engine = LogicEngine(lmm_interface=lmm_interface, logger=self.mock_logger)
        logic_engine.state_engine.state["sexual_arousal"] = 80 # Above threshold 50

        # Mock time and state
        logic_engine.last_lmm_call_time = time.time() - 3 # Normal interval is 5, accelerated is 2.5
        logic_engine.current_mode = "active"

        # Run update
        with patch.object(logic_engine, '_trigger_lmm_analysis') as mock_trigger:
            logic_engine.update()
            mock_trigger.assert_called_with(reason="high_sexual_arousal", allow_intervention=True)

if __name__ == '__main__':
    unittest.main()
