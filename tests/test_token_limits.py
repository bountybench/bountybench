# tests/test_token_limits.py

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from resources.model_resource.model_resource import ModelResourceConfig
from workflows.exploit_and_patch_workflow import ExploitAndPatchWorkflow

class TestTokenLimits(unittest.TestCase):

    @patch("workflows.bounty_workflow.read_repo_metadata") 
    @patch("workflows.bounty_workflow.read_bounty_metadata")  
    @patch("agents.executor_agent.executor_agent.ExecutorAgent", autospec=True)
    def test_workflow_token_limits(self, mock_executor, mock_bounty_metadata, mock_repo_metadata):
        """Test token limits are correctly passed through workflow"""
        # Mock metadata returns
        mock_repo_metadata.return_value = {"target_host": "localhost"}
        mock_bounty_metadata.return_value = {"files_dir": "codebase", "vulnerable_commit": "main"}

        # Create workflow with custom token limits
        workflow = ExploitAndPatchWorkflow(
            task_dir=Path("/tmp"),
            bounty_number="0",
            max_input_tokens=2048,
            max_output_tokens=1024
        )

        # Check token limits in model resources
        for phase in workflow._phase_graph.keys():
            resources = phase.define_resources()
            if 'model' in resources:
                model_config = resources['model'][1]
                self.assertEqual(model_config.max_input_tokens, 2048)
                self.assertEqual(model_config.max_output_tokens, 1024)

if __name__ == '__main__':
    unittest.main()