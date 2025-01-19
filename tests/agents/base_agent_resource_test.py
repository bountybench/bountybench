import unittest
from unittest.mock import MagicMock, patch
from typing import List

from resources.base_resource import BaseResource
from messages.message import Message
from agents.base_agent import BaseAgent, AgentConfig, ResourceNotInitializedError

class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)

    def stop(self):
        pass

class TestAgent(BaseAgent):
    REQUIRED_RESOURCES = [(MockResource, "mock_resource")]
    OPTIONAL_RESOURCES = [(MockResource, "optional_resource")]
    ACCESSIBLE_RESOURCES = [(MockResource, "mock_resource"), (MockResource, "optional_resource")]

    def run(self, messages: List[Message]) -> Message:
        # This should raise an error if not initialized
        return Message(f"Test message with {self.mock_resource}")

class TestBaseAgentResourceAccess(unittest.TestCase):

    def setUp(self):
        self.agent_config = AgentConfig(id="test_agent")
        self.mock_resource_manager = MagicMock()
        self.agent = TestAgent(self.agent_config, self.mock_resource_manager)

    def test_wrapped_run_without_initialization(self):
        with self.assertRaises(ResourceNotInitializedError):
            self.agent.run([])

    def test_access_uninitialized_resource(self):
        with self.assertRaises(ResourceNotInitializedError):
            _ = self.agent.mock_resource

    def test_register_and_access_resource(self):
        mock_resource = MockResource("mock_resource", {})
        self.mock_resource_manager.get_resource.return_value = mock_resource
        
        self.agent.register_resources()
        
        self.assertEqual(self.agent.mock_resource, mock_resource)
        message = self.agent.run([])
        self.assertEqual(message.message, "Test message with mock_resource")

if __name__ == '__main__':
    unittest.main()