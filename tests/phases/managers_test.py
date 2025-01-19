import unittest
from unittest.mock import Mock, patch
from typing import Dict, List, Optional, Tuple, Type

from workflows.base_workflow import BaseWorkflow
from phases.base_phase import BasePhase
from agents.base_agent import BaseAgent, AgentConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from agents.agent_manager import AgentManager
from resources.resource_manager import ResourceManager
from dataclasses import dataclass

# Create a mock for workflow_logger
mock_workflow_logger = Mock()
mock_workflow_logger.add_resource = Mock()
mock_workflow_logger.add_agent = Mock()
mock_workflow_logger.phase = Mock()

# Mock resources and agents for testing
class MockResource(BaseResource):
    def __init__(self, resource_id: str, config: Optional[BaseResourceConfig] = None):
        super().__init__(resource_id, config)
        self.initialized = True

    def stop(self):
        self.initialized = False

@dataclass 
class MockAgentConfig1:
    id: str

class MockAgent1(BaseAgent):
    CONFIG_CLASS = MockAgentConfig1

    REQUIRED_RESOURCES=[(MockResource, "resource1"), (MockResource, "resource2")]

    def __init__(self, agent_id: str, config: AgentConfig):
        super().__init__(agent_id, config)
        self.resources = {}

    def run(self):
        pass

@dataclass 
class MockAgentConfig2:
    id: str

class MockAgent2(BaseAgent):
    CONFIG_CLASS = MockAgentConfig2   
    
    REQUIRED_RESOURCES=[(MockResource, "resource2"), (MockResource, "resource3")]

    def __init__(self, agent_id: str, config: AgentConfig):
        super().__init__(agent_id, config)
        self.resources = {}

    def run(self):
        pass

class MockPhase1(BasePhase):
    AGENT_CLASSES = [MockAgent1]

    def define_resources(self) -> Dict[str, Tuple[Type[BaseResource], Optional[BaseResourceConfig]]]:
        return {
            "resource1": (MockResource, None),
            "resource2": (MockResource, None)
        }

    def define_agents(self) -> List[Tuple[str, AgentConfig]]:
        return [("agent1", MockAgentConfig1("agent1"))]

    def run_one_iteration(self, phase_message, agent_instance, previous_output):
        pass

class MockPhase2(BasePhase):
    AGENT_CLASSES = [MockAgent2]

    def define_resources(self) -> Dict[str, Tuple[Type[BaseResource], Optional[BaseResourceConfig]]]:
        return {
            "resource2": (MockResource, None),
            "resource3": (MockResource, None)
        }

    def define_agents(self) -> List[Tuple[str, AgentConfig]]:
        return [("agent2", MockAgentConfig2("agent2"))]

    def run_one_iteration(self, phase_message, agent_instance, previous_output):
        pass

@patch('resources.resource_manager.workflow_logger', mock_workflow_logger)
@patch('phases.base_phase.workflow_logger', mock_workflow_logger)
@patch('agents.base_agent.workflow_logger', mock_workflow_logger)
class TestPhaseResourceAndAgentHandling(unittest.TestCase):

    def setUp(self):
        self.workflow = Mock(spec=BaseWorkflow)
        self.workflow.resource_manager = ResourceManager()
        self.workflow.agent_manager = AgentManager()

    @patch('resources.resource_manager.workflow_logger', mock_workflow_logger)
    @patch('phases.base_phase.workflow_logger', mock_workflow_logger)
    @patch('agents.base_agent.workflow_logger', mock_workflow_logger)
    def test_resource_and_agent_handling(self):
        # Create phases with explicit phase indices
        phase1 = MockPhase1(self.workflow)
        phase1.phase_config.phase_idx = 0
        phase2 = MockPhase2(self.workflow)
        phase2.phase_config.phase_idx = 1
        self.workflow.phases = [phase1, phase2]

        # Compute resource schedule
        self.workflow.resource_manager.compute_schedule(self.workflow.phases)
        
        # Setup and run Phase 1
        phase1.setup()
        self.assertEqual(len(self.workflow.resource_manager.resources), 2)
        self.assertTrue(self.workflow.resource_manager.resources["resource1"].initialized)
        self.assertTrue(self.workflow.resource_manager.resources["resource2"].initialized)
        self.assertEqual(len(self.workflow.agent_manager._agents), 1)
        self.assertIn("agent1", self.workflow.agent_manager._agents)

        # Simulate end of Phase 1
        self.workflow.resource_manager.deallocate_phase_resources(0)
        self.assertNotIn("resource1", self.workflow.resource_manager.resources) 
        self.assertIn("resource2", self.workflow.resource_manager.resources)  
        self.assertTrue(self.workflow.resource_manager.resources["resource2"].initialized)  

        # Setup and run Phase 2
        phase2.setup()
        self.assertEqual(len(self.workflow.resource_manager.resources), 2)  # Changed this line
        self.assertNotIn("resource1", self.workflow.resource_manager.resources)  # Added this line
        self.assertTrue(self.workflow.resource_manager.resources["resource2"].initialized)
        self.assertTrue(self.workflow.resource_manager.resources["resource3"].initialized)
        self.assertEqual(len(self.workflow.agent_manager._agents), 2)
        self.assertIn("agent1", self.workflow.agent_manager._agents)
        self.assertIn("agent2", self.workflow.agent_manager._agents)

        # Simulate end of Phase 2
        self.workflow.resource_manager.deallocate_phase_resources(1)
        self.assertNotIn("resource1", self.workflow.resource_manager.resources)
        self.assertNotIn("resource2", self.workflow.resource_manager.resources)
        self.assertNotIn("resource3", self.workflow.resource_manager.resources)
        self.assertEqual(len(self.workflow.resource_manager.resources), 0)  # Added this line

        # Assert that the mocked workflow_logger methods were called
        mock_workflow_logger.add_resource.assert_called()
        mock_workflow_logger.add_agent.assert_called()

if __name__ == '__main__':
    unittest.main()