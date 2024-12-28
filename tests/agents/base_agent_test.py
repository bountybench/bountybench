import unittest
from unittest.mock import MagicMock, patch
from typing import List

from resources.base_resource import BaseResource
from responses.base_response import BaseResponse
from responses.response import Response
from agents.base_agent import BaseAgent, AgentConfig, ResourceNotInitializedError

class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)

    def stop(self):
        pass

class MockAgent(BaseAgent):
    REQUIRED_RESOURCES = [(MockResource, "mock_resource")]
    OPTIONAL_RESOURCES = [(MockResource, "optional_resource")]
    ACCESSIBLE_RESOURCES = [(MockResource, "mock_resource"), (MockResource, "optional_resource")]

    def run(self, responses: List[Response]) -> Response:
        # Access a required resource to test initialization
        self.mock_resource
        return BaseResponse("Mock response")

class TestBaseAgent(unittest.TestCase):

    def setUp(self):
        self.agent_config = AgentConfig(id="test_agent")
        self.mock_resource_manager = MagicMock()
        self.agent = MockAgent(self.agent_config, self.mock_resource_manager)

    def test_initialization(self):
        self.assertFalse(self.agent._resources_initialized)
        with self.assertRaises(ResourceNotInitializedError):
            _ = self.agent.mock_resource
        self.assertIsNone(self.agent.optional_resource)

    def test_register_resources_success(self):
        mock_resource = MockResource("mock_resource", {})
        self.mock_resource_manager.get_resource.side_effect = [mock_resource, mock_resource]
        
        self.agent.register_resources()
        
        self.assertTrue(self.agent._resources_initialized)
        self.assertEqual(self.agent.mock_resource, mock_resource)
        self.assertEqual(self.agent.optional_resource, mock_resource)

    def test_register_resources_missing_required(self):
        self.mock_resource_manager.get_resource.side_effect = [KeyError, MockResource("optional", {})]
        
        with self.assertRaises(KeyError):
            self.agent.register_resources()
        
        self.assertFalse(self.agent._resources_initialized)

    def test_register_resources_missing_optional(self):
        mock_resource = MockResource("mock_resource", {})
        self.mock_resource_manager.get_resource.side_effect = [mock_resource, KeyError]
        
        self.agent.register_resources()
        
        self.assertTrue(self.agent._resources_initialized)
        self.assertEqual(self.agent.mock_resource, mock_resource)
        self.assertIsNone(self.agent.optional_resource)

    def test_run_without_initialization(self):
        with self.assertRaises(ResourceNotInitializedError):
            self.agent.run([])

    def test_run_after_initialization(self):
        mock_resource = MockResource("mock_resource", {})
        self.mock_resource_manager.get_resource.side_effect = [mock_resource, mock_resource]
        self.agent.register_resources()

        response = self.agent.run([])
        self.assertIsInstance(response, BaseResponse)
        self.assertEqual(response.response, "Mock response")

    def test_access_uninitialized_required_resource(self):
        with self.assertRaises(ResourceNotInitializedError):
            _ = self.agent.mock_resource

    def test_access_uninitialized_optional_resource(self):
        self.assertIsNone(self.agent.optional_resource)

    @patch('agents.base_agent.logger.warning')
    def test_register_resources_logs_warning_for_missing_optional(self, mock_warning):
        mock_resource = MockResource("mock_resource", {})
        self.mock_resource_manager.get_resource.side_effect = [mock_resource, KeyError]
        
        self.agent.register_resources()
        
        mock_warning.assert_called_once_with("Optional resource 'optional_resource' not allocated. Attribute remains None.")

if __name__ == '__main__':
    unittest.main()