from typing import Any, Dict, List, Tuple, Union
from unittest.mock import MagicMock, patch
import pytest

from agents.base_agent import BaseAgent
from phases.base_phase import BasePhase, PhaseConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.resource_manager import ResourceManager


class MockResourceConfig(BaseResourceConfig):
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}


class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)
        self.initialized = True

    def stop(self):
        self.initialized = False


class MockAgent1(BaseAgent):
    REQUIRED_RESOURCES: List[Union[type, Tuple[type, str]]] = [
        (MockResource, "resource1"),
        (MockResource, "resource2"),
    ]


class MockAgent2(BaseAgent):
    REQUIRED_RESOURCES: List[Union[type, Tuple[type, str]]] = [
        (MockResource, "resource2"),
        (MockResource, "resource3"),
    ]


class MockPhase1(BasePhase):
    REQUIRED_AGENTS = [MockAgent1]

    def define_resources(self):
        return {
            "resource1": (MockResource, MockResourceConfig()),
            "resource2": (MockResource, MockResourceConfig()),
        }

    def define_agents(self):
        pass

    def run_one_iteration(self, phase_message, agent_instance, previous_output):
        pass

    @classmethod
    def get_required_resources(cls):
        return {"resource1", "resource2"}


class MockPhase2(BasePhase):
    REQUIRED_AGENTS = [MockAgent1, MockAgent2]

    def define_resources(self):
        return {
            "resource1": (MockResource, MockResourceConfig()),
            "resource2": (MockResource, MockResourceConfig()),
            "resource3": (MockResource, MockResourceConfig()),
        }

    def define_agents(self):
        pass

    def run_one_iteration(self, phase_message, agent_instance, previous_output):
        pass

    @classmethod
    def get_required_resources(cls):
        return {"resource1", "resource2", "resource3"}


@pytest.fixture
def resource_manager():
    return ResourceManager()


@pytest.fixture
def mock_workflow():
    workflow = MagicMock()
    workflow.resource_manger = MagicMock()
    workflow.agent_manager = MagicMock()
    return workflow


@patch("utils.logger.get_main_logger")
def test_resource_lifecycle(mock_logger, resource_manager, mock_workflow):
    # Register resources
    for i in range(1, 4):
        resource_manager.register_resource(
            f"resource{i}", MockResource, MockResourceConfig()
        )

    phases = [MockPhase1(mock_workflow), MockPhase2(mock_workflow)]
    
    # Compute schedule
    resource_manager.compute_schedule(phases)

    # Check resource lifecycle
    assert resource_manager._resource_lifecycle["resource1"] == (0, 1)
    assert resource_manager._resource_lifecycle["resource2"] == (0, 1)
    assert resource_manager._resource_lifecycle["resource3"] == (1, 1)

    # Initialize resources for Phase1
    resource_manager.initialize_phase_resources(0, MockPhase1.get_required_resources())
    assert "resource1" in resource_manager._resources
    assert "resource2" in resource_manager._resources
    assert "resource3" not in resource_manager._resources

    # Deallocate resources after Phase1
    resource_manager.deallocate_phase_resources(0)
    assert "resource1" in resource_manager._resources
    assert "resource2" in resource_manager._resources

    # Initialize resources for Phase2
    resource_manager.initialize_phase_resources(1, MockPhase2.get_required_resources())
    assert "resource1" in resource_manager._resources
    assert "resource2" in resource_manager._resources
    assert "resource3" in resource_manager._resources

    # Deallocate resources after Phase2
    resource_manager.deallocate_phase_resources(1)
    assert "resource1" not in resource_manager._resources
    assert "resource2" not in resource_manager._resources
    assert "resource3" not in resource_manager._resources


@patch("utils.logger.get_main_logger")
def test_get_resource(mock_logger, resource_manager, mock_workflow):
    resource_manager.register_resource("resource1", MockResource, MockResourceConfig())
    resource_manager.register_resource("resource2", MockResource, MockResourceConfig())
    resource_manager.compute_schedule([MockPhase1(mock_workflow)])
    resource_manager.initialize_phase_resources(0, MockPhase1.get_required_resources())

    resource = resource_manager.get_resource("resource1")
    assert isinstance(resource, MockResource)

    resource = resource_manager.get_resource("resource2")
    assert isinstance(resource, MockResource)

    with pytest.raises(KeyError):
        resource_manager.get_resource("non_existent_resource")
