import pytest
from typing import List

from resources.base_resource import BaseResource
from resources.default_resource import DefaultResource
from messages.message import Message
from agents.base_agent import BaseAgent, AgentConfig

class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)

    def stop(self):
        pass

class MockAgent(BaseAgent):
    REQUIRED_RESOURCES = [DefaultResource.BOUNTY_RESOURCE, DefaultResource.DOCKER]
    OPTIONAL_RESOURCES = [DefaultResource.INIT_FILES]
    ACCESSIBLE_RESOURCES = [DefaultResource.BOUNTY_RESOURCE, DefaultResource.DOCKER, DefaultResource.INIT_FILES]

    def run(self, messages: List[Message]) -> Message:
        self.mock_resource
        return Message("Mock message")

@pytest.fixture
def agent():
    agent_config = AgentConfig()
    return MockAgent('mock_agent', agent_config)

# TODO: test feels like it shouldn't be this
def test_initialization(agent):
    with pytest.raises(AttributeError):
        _ = agent.mock_resource

def test_get_resources(agent):
    required = agent.get_required_resources()
    optional = agent.get_optional_resources()

    assert required == {str(DefaultResource.BOUNTY_RESOURCE), str(DefaultResource.DOCKER)}
    assert optional == {str(DefaultResource.INIT_FILES)}
