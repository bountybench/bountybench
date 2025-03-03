from typing import Any, Dict, List, Tuple, Union
from unittest.mock import MagicMock, patch

import pytest

from agents.base_agent import BaseAgent
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.resource_manager import ResourceManager
from resources.resource_type import ResourceType

RESOURCE1 = ResourceType.DOCKER
RESOURCE2 = ResourceType.INIT_FILES
RESOURCE3 = ResourceType.BOUNTY_RESOURCE
RESOURCE4 = ResourceType.REPO_RESOURCE
RESOURCES = [RESOURCE1, RESOURCE2, RESOURCE3, RESOURCE4]


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
    REQUIRED_RESOURCES: List[ResourceType] = [
        RESOURCE1,
        RESOURCE2,
    ]


class MockAgent2(BaseAgent):
    REQUIRED_RESOURCES: List[Union[type, Tuple[type, str]]] = [
        RESOURCE3,
        RESOURCE4,
    ]


class MockPhase1(BasePhase):
    REQUIRED_AGENTS = [MockAgent1]

    def define_resources(self):
        return [
            (RESOURCE1, MockResourceConfig()),
            (RESOURCE2, MockResourceConfig()),
        ]

    def define_agents(self):
        pass

    def run_one_iteration(self, phase_message, agent_instance, previous_output):
        pass

    @classmethod
    def get_required_resources(cls):
        return {str(RESOURCE1), str(RESOURCE2)}


class MockPhase2(BasePhase):
    REQUIRED_AGENTS = [MockAgent1, MockAgent2]

    def define_resources(self):
        return [
            (RESOURCE1, MockResourceConfig()),
            (RESOURCE2, MockResourceConfig()),
            (RESOURCE3, MockResourceConfig()),
        ]

    def define_agents(self):
        pass

    def run_one_iteration(self, phase_message, agent_instance, previous_output):
        pass

    @classmethod
    def get_required_resources(cls):
        return {str(RESOURCE1), str(RESOURCE2), str(RESOURCE3)}


@pytest.fixture
def resource_manager():
    return ResourceManager(workflow_id=1)


@pytest.fixture
def mock_workflow():
    workflow = MagicMock()
    workflow.resource_manger = MagicMock()
    workflow.agent_manager = MagicMock()
    return workflow


@pytest.fixture
def mock_resource_constructors():
    def mock_init(self, resource_id=None, config=None):
        return None

    mocks = [
        patch.object(resource.get_class(), "__init__", mock_init)
        for resource in RESOURCES
    ]
    mocks.extend(
        [
            patch.object(resource.get_class(), "stop", mock_init)
            for resource in RESOURCES
        ]
    )
    [mock.start() for mock in mocks]
    yield
    patch.stopall()


def test_resource_lifecycle(
    resource_manager, mock_workflow, mock_resource_constructors
):
    # Register resources
    for resource in RESOURCES:
        resource_manager.register_resource(
            str(resource), MockResource, MockResourceConfig()
        )

    phases = [MockPhase1(mock_workflow), MockPhase2(mock_workflow)]

    # Compute schedule
    resource_manager.compute_schedule(phases)

    # Check resource lifecycle
    assert resource_manager._resource_lifecycle[str(RESOURCE1)] == (0, 1)
    assert resource_manager._resource_lifecycle[str(RESOURCE2)] == (0, 1)
    assert resource_manager._resource_lifecycle[str(RESOURCE3)] == (1, 1)

    # Initialize resources for Phase1
    resource_manager.initialize_phase_resources(0, MockPhase1.get_required_resources())
    assert resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE1)
    )
    assert resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE2)
    )
    assert not resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE3)
    )

    # Deallocate resources after Phase1
    resource_manager.deallocate_phase_resources(0)
    assert resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE1)
    )
    assert resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE2)
    )
    # Initialize resources for Phase2
    resource_manager.initialize_phase_resources(1, MockPhase2.get_required_resources())
    assert resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE1)
    )
    assert resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE2)
    )
    assert resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE3)
    )

    # Deallocate resources after Phase2
    resource_manager.deallocate_phase_resources(1)
    assert not resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE1)
    )
    assert not resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE2)
    )
    assert not resource_manager._resources.contains(
        workflow_id=1, resource_id=str(RESOURCE3)
    )


def test_get_resource(resource_manager, mock_workflow, mock_resource_constructors):
    resource_manager.register_resource(
        str(RESOURCE1), MockResource, MockResourceConfig()
    )
    resource_manager.register_resource(
        str(RESOURCE2), MockResource, MockResourceConfig()
    )
    resource_manager.compute_schedule([MockPhase1(mock_workflow)])
    resource_manager.initialize_phase_resources(0, MockPhase1.get_required_resources())

    resource = resource_manager.get_resource(str(RESOURCE1))
    assert isinstance(resource, RESOURCE1.get_class())

    resource = resource_manager.get_resource(str(RESOURCE2))
    assert isinstance(resource, RESOURCE2.get_class())

    with pytest.raises(KeyError):
        resource_manager.get_resource("non_existent_resource")
