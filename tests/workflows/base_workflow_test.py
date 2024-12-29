import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import List, Type

from agents.base_agent import BaseAgent, AgentConfig
from phases.base_phase import BasePhase, PhaseConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from responses.base_response import BaseResponse
from workflows.base_workflow import BaseWorkflow, WorkflowConfig, WorkflowStatus

class MockAgent(BaseAgent):
    def __init__(self, agent_config: AgentConfig, resource_manager):
        super().__init__(agent_config, resource_manager)

    def run(self, response):
        pass
    
class MockPhase(BasePhase):
    @classmethod
    def get_required_resources(cls) -> List[str]:
        return ["mock_resource"]

    def run_phase(self):
        return BaseResponse("Mock response"), True

    def run_one_iteration(self, agent_instance, previous_output, iteration_num):
        pass
    
class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)

    def stop(self):
        pass

class MockWorkflow(BaseWorkflow):
    def get_initial_prompt(self) -> str:
        return "Mock initial prompt"

    def define_agent_configs(self) -> None:
        agent_config = AgentConfig(id="mock_agent")
        self.register_agent(MockAgent, agent_config)

    def define_phase_configs(self) -> None:
        phase_config = PhaseConfig(
            phase_idx=0,
            phase_name=MockPhase,
            max_iterations=1,
            agents=[("mock_agent", self.agents["mock_agent"])]
        )
        self.register_phase(MockPhase, phase_config)

    def define_resource_configs(self) -> None:
        super().define_resource_configs()
        mock_resource_config = BaseResourceConfig()
        self.register_resource("mock_resource", MockResource, mock_resource_config)

    def setup_directories(self) -> None:
        pass

@patch("workflows.base_workflow.read_repo_metadata")
@patch("workflows.base_workflow.read_bounty_metadata")
@patch("workflows.base_workflow.docker_network_exists")
@patch("workflows.base_workflow.run_command")
@patch("resources.init_files_resource.InitFilesResourceConfig.validate")
class TestBaseWorkflow(unittest.TestCase):
    def setUp(self):
        self.task_repo_dir = Path("/mock/path")
        self.bounty_number = "1"

    def test_workflow_initialization(self, mock_validate, mock_run_command, mock_docker_network_exists, 
                                     mock_read_bounty_metadata, mock_read_repo_metadata):
        mock_read_repo_metadata.return_value = {}
        mock_read_bounty_metadata.return_value = {}
        mock_docker_network_exists.return_value = True
        mock_validate.return_value = None  # Bypass validation

        workflow = MockWorkflow(self.task_repo_dir, self.bounty_number)
        
        self.assertEqual(workflow.status, WorkflowStatus.INITIALIZED)
        self.assertIsInstance(workflow.config, WorkflowConfig)
        self.assertEqual(len(workflow.config.phase_configs), 1)
        self.assertIn("mock_agent", workflow.agents)
        self.assertIn("init_files", workflow.resource_manager._resource_registration)

    def test_run_phases(self, mock_validate, mock_run_command, mock_docker_network_exists, 
                        mock_read_bounty_metadata, mock_read_repo_metadata):
        mock_read_repo_metadata.return_value = {}
        mock_read_bounty_metadata.return_value = {}
        mock_docker_network_exists.return_value = True
        mock_validate.return_value = None  # Bypass validation

        workflow = MockWorkflow(self.task_repo_dir, self.bounty_number)
        
        for phase_response, phase_success in workflow.run_phases():
            self.assertIsInstance(phase_response, BaseResponse)
            self.assertTrue(phase_success)

        self.assertEqual(workflow.status, WorkflowStatus.COMPLETED_SUCCESS)

    @patch("workflows.base_workflow.BaseWorkflow.setup_phase_resources")
    @patch("workflows.base_workflow.BaseWorkflow.setup_phase_agents")
    def test_setup_phase(self, mock_setup_agents, mock_setup_resources, 
                         mock_validate, mock_run_command, mock_docker_network_exists, 
                         mock_read_bounty_metadata, mock_read_repo_metadata):
        mock_read_repo_metadata.return_value = {}
        mock_read_bounty_metadata.return_value = {}
        mock_docker_network_exists.return_value = True
        mock_validate.return_value = None  # Bypass validation

        workflow = MockWorkflow(self.task_repo_dir, self.bounty_number)
        phase = workflow.setup_phase(0)

        mock_setup_resources.assert_called_once_with(0)
        mock_setup_agents.assert_called_once_with(0)
        self.assertIsInstance(phase, MockPhase)

    def test_register_resource(self, mock_validate, mock_run_command, mock_docker_network_exists, 
                               mock_read_bounty_metadata, mock_read_repo_metadata):
        mock_read_repo_metadata.return_value = {}
        mock_read_bounty_metadata.return_value = {}
        mock_docker_network_exists.return_value = True
        mock_validate.return_value = None  # Bypass validation

        workflow = MockWorkflow(self.task_repo_dir, self.bounty_number)
        
        resource_config = BaseResourceConfig()
        workflow.register_resource("test_resource", MockResource, resource_config)

        self.assertIn("test_resource", workflow.resource_manager._resource_registration)

if __name__ == "__main__":
    unittest.main()