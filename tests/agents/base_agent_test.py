import unittest
from typing import List
from unittest.mock import MagicMock, patch

from agents.base_agent import AgentConfig, BaseAgent, ResourceNotInitializedError
from messages.message import Message
from resources.base_resource import BaseResource


class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)

    def stop(self):
        pass


class MockAgent(BaseAgent):
    REQUIRED_RESOURCES = [(MockResource, "mock_resource")]
    OPTIONAL_RESOURCES = [(MockResource, "optional_resource")]
    ACCESSIBLE_RESOURCES = [
        (MockResource, "mock_resource"),
        (MockResource, "optional_resource"),
    ]

    def run(self, messages: List[Message]) -> Message:
        # Access a required resource to test initialization
        self.mock_resource
        return Message("Mock message")


class TestBaseAgent(unittest.TestCase):

    def setUp(self):
        self.agent_config = AgentConfig()
        self.mock_resource_manager = MagicMock()
        self.agent = MockAgent("mock_agent", self.agent_config)

    def test_initialization(self):
        with self.assertRaises(AttributeError):
            _ = self.agent.mock_resource

    def test_get_resources(self):
        optional = self.agent.get_optional_resources()
        required = self.agent.get_required_resources()

        self.assertSetEqual(optional, {self.agent.OPTIONAL_RESOURCES[0][1]})
        self.assertSetEqual(required, {self.agent.REQUIRED_RESOURCES[0][1]})


if __name__ == "__main__":
    unittest.main()
