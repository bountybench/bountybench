from typing import List

import pytest

from agents.base_agent import AgentConfig, BaseAgent
from messages.message import Message
from resources.base_resource import BaseResource
from resources.default_resource import DefaultResource


class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)

    def stop(self):
        pass


class MockAgent(BaseAgent):
    REQUIRED_RESOURCES = [DefaultResource.INIT_FILES]
    OPTIONAL_RESOURCES = [DefaultResource.DOCKER]
    ACCESSIBLE_RESOURCES = [
        DefaultResource.INIT_FILES,
        DefaultResource.DOCKER,
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


def test_get_resources(agent):
    optional = agent.get_optional_resources()
    required = agent.get_required_resources()
    accessible = agent.get_accessible_resources()

    assert optional == {"docker"}
    assert required == {"init_files"}
    assert accessible == {"init_files", "docker"}
