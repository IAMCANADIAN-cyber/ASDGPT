import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add root directory to sys.path
sys.path.append(os.getcwd())

import config
from core.lmm_interface import LMMInterface

class TestLMMURLConstruction(unittest.TestCase):

    @patch('core.lmm_interface.InterventionLibrary')
    def test_url_construction_variations(self, mock_lib):
        # Setup mock library
        mock_lib.return_value.get_all_interventions_info.return_value = ""

        test_cases = [
            ("http://127.0.0.1:1234", "http://127.0.0.1:1234/v1/chat/completions"),
            ("http://127.0.0.1:1234/v1", "http://127.0.0.1:1234/v1/chat/completions"),
            ("http://127.0.0.1:1234/api/v1/chat", "http://127.0.0.1:1234/api/v1/chat/completions"),
            ("http://127.0.0.1:1234/v1/chat/completions", "http://127.0.0.1:1234/v1/chat/completions"),
            ("http://localhost:5000/api/v1", "http://localhost:5000/api/v1/chat/completions"),
            # Trailing slashes should be handled by rstrip in code
            ("http://127.0.0.1:1234/", "http://127.0.0.1:1234/v1/chat/completions"),
        ]

        for input_url, expected_url in test_cases:
            with patch.object(config, 'LOCAL_LLM_URL', input_url):
                lmm = LMMInterface(data_logger=None, intervention_library=None)
                self.assertEqual(lmm.llm_url, expected_url, f"Failed for input: {input_url}")

if __name__ == '__main__':
    unittest.main()
