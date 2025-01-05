import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from resources.resource_manager import ResourceManager
from workflows.base_workflow import BaseWorkflow
from phases.base_phase import BasePhase, PhaseConfig
from agents.base_agent import AgentConfig, BaseAgent
from resources.base_resource import BaseResource
from resources.init_files_resource import InitFilesResourceConfig

class TestResource1(BaseResource):
    pass

class TestResource2(BaseResource):
    pass

class TestResource3(BaseResource):
    pass

class TestAgent1(BaseAgent):
    REQUIRED_RESOURCES = [TestResource1]
    def run(self, response):
        pass

class TestAgent2(BaseAgent):
    REQUIRED_RESOURCES = [TestResource2]
    def run(self, response):
        pass

class TestAgent3(BaseAgent):
    REQUIRED_RESOURCES = [TestResource3]
    def run(self, response):
        pass
    
class TestPhase1(BasePhase):
    REQUIRED_AGENTS = [TestAgent1, TestAgent2]

class TestPhase2(BasePhase):
    REQUIRED_AGENTS = [TestAgent3]

class TestWorkflow(BaseWorkflow):
    REQUIRED_PHASES = [TestPhase1, TestPhase2]

    def get_initial_prompt(self):
        return "Test prompt"

    def define_resource_configs(self):
        super().define_resource_configs()
        # Register test resources
        self.register_resource("TestResource1", TestResource1, Mock())
        self.register_resource("TestResource2", TestResource2, Mock())
        self.register_resource("TestResource3", TestResource3, Mock())
            
    def define_agent_configs(self):
        # Mock agent configurations
        self.register_agent(TestAgent1, AgentConfig(id="agent1"))
        self.register_agent(TestAgent2, AgentConfig(id="agent2"))
        self.register_agent(TestAgent3, AgentConfig(id="agent3"))
    
    def define_phase_configs(self):
        # Mock phase configurations
        self.register_phase(TestPhase1, PhaseConfig(phase_idx=0, phase_name="TestPhase1", max_iterations=5, agents=[]))
        self.register_phase(TestPhase2, PhaseConfig(phase_idx=1, phase_name="TestPhase2", max_iterations=5, agents=[]))

    def setup_directories(self):
        pass

class TestBaseWorkflowValidation(unittest.TestCase):
    @patch('workflows.base_workflow.read_repo_metadata')
    @patch('workflows.base_workflow.read_bounty_metadata')
    @patch('workflows.base_workflow.docker_network_exists')
    @patch('workflows.base_workflow.run_command')
    @patch('workflows.base_workflow.InitFilesResourceConfig')
    @patch('workflows.base_workflow.InitFilesResource')
    @patch('workflows.base_workflow.SetupResource')
    def setUp(self, mock_setup_resource, mock_init_files_resource, mock_init_files_config, 
              mock_run_command, mock_docker_network_exists, mock_read_bounty_metadata, mock_read_repo_metadata):
        mock_read_repo_metadata.return_value = {}
        mock_read_bounty_metadata.return_value = {}
        mock_docker_network_exists.return_value = True
        mock_init_files_config.return_value = Mock(spec=InitFilesResourceConfig)
        
        mock_init_files_resource.__name__ = "InitFilesResource"
        mock_init_files_resource.return_value = Mock(spec=BaseResource)
        
        mock_setup_resource.__name__ = "SetupResource"
        mock_setup_resource.return_value = Mock(spec=BaseResource)

        # Create the workflow without calling validate_registrations
        self.workflow = TestWorkflow(Path('/test/path'), '123')
        
        # Manually call the configuration methods
        self.workflow.define_resource_configs()
        self.workflow.define_agent_configs()
        self.workflow.define_phase_configs()
        
        # Manually set up the phase_class_map
        self.workflow.phase_class_map = {
            'TestPhase1': TestPhase1,
            'TestPhase2': TestPhase2
        }

    def test_validate_required_phases(self):
        self.workflow.validate_registrations() 
        
        # Test for missing phase
        self.workflow.phase_class_map = {'TestPhase1': TestPhase1}
        with self.assertRaises(ValueError) as context:
            self.workflow._validate_required_phases()
        self.assertIn("Missing required phases: TestPhase2", str(context.exception))

    def test_validate_required_agents(self):
        # First, ensure the agents are properly registered
        self.workflow.agents = {
            'agent1': TestAgent1(AgentConfig(id="agent1"), self.workflow.resource_manager),
            'agent2': TestAgent2(AgentConfig(id="agent2"), self.workflow.resource_manager),
            'agent3': TestAgent3(AgentConfig(id="agent3"), self.workflow.resource_manager)
        }
        self.workflow._validate_required_agents()  # Should not raise an exception

        # Now test for missing agent
        self.workflow.agents = {'agent1': TestAgent1(AgentConfig(id="agent1"), self.workflow.resource_manager)}
        with self.assertRaises(ValueError) as context:
            self.workflow._validate_required_agents()
        self.assertIn("Missing required agents for TestPhase1: TestAgent2", str(context.exception))

    def test_validate_required_resources(self):
        # First, ensure all resources are properly registered
        self.workflow.resource_manager.register_resource("TestResource1", TestResource1, Mock())
        self.workflow.resource_manager.register_resource("TestResource2", TestResource2, Mock())
        self.workflow.resource_manager.register_resource("TestResource3", TestResource3, Mock())
        
        self.workflow._validate_required_resources()  # Should not raise an exception

        # Now test for missing resource
        # We can't directly modify resources, so let's create a new ResourceManager with missing resources
        new_resource_manager = ResourceManager()
        new_resource_manager.register_resource("TestResource1", TestResource1, Mock())
        self.workflow.resource_manager = new_resource_manager

        with self.assertRaises(ValueError) as context:
            self.workflow._validate_required_resources()
        self.assertIn("Missing required resources:", str(context.exception))
        self.assertIn("TestResource2", str(context.exception))
        self.assertIn("TestResource3", str(context.exception))

if __name__ == '__main__':
    unittest.main()