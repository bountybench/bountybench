from typing import List

import pytest

from agents.base_agent import AgentConfig, BaseAgent
from messages.message import Message
from resources.base_resource import BaseResource
from resources.resource_type import ResourceType


class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)

    def stop(self):
        pass


class MockAgent(BaseAgent):
    REQUIRED_RESOURCES = [ResourceType.INIT_FILES]
    OPTIONAL_RESOURCES = [ResourceType.DOCKER]
    ACCESSIBLE_RESOURCES = [
        ResourceType.INIT_FILES,
        ResourceType.DOCKER,
    ]

    def run(self, messages: List[Message]) -> Message:
        self.mock_resource
        return Message("Mock message")


@pytest.fixture
def agent():
    agent_config = AgentConfig()
    return MockAgent("mock_agent", agent_config)


def test_initialization(agent):
    with pytest.raises(AttributeError):
        _ = agent.mock_resource
