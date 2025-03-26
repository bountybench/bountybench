from resources.bounty_setup_resource import BountySetupResource
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.memory_resource.memory_resource import MemoryResource
from resources.model_resource.model_resource import ModelResource
from resources.repo_setup_resource import RepoSetupResource
from resources.resource_type import AgentResources, ResourceType
from tests.test_utils.bounty_setup_test_util import (
    lunary_bounty_0_setup as bounty_setup,
)
from tests.test_utils.bounty_setup_test_util import workflow_id


# Note: most of these tests assume that DOCKER exists in bounty_setup and MEMORY does not.
def test_has_bound_true():
    am = AgentResources()
    am.docker = "mock_resource"  # Simulate the resource being bound

    # Check if the resource is bound
    assert am.has_bound(ResourceType.DOCKER)


def test_has_bound_false():
    am = AgentResources()

    # Check if the resource is not bound
    assert not am.has_bound(ResourceType.DOCKER)


def test_exists_found(bounty_setup):
    assert ResourceType.DOCKER.exists(workflow_id)


def test_exists_not_found(bounty_setup):
    assert not ResourceType.MEMORY.exists(workflow_id)


def test_resource_type_str():
    assert str(ResourceType.DOCKER) == "docker"
    assert str(ResourceType.INIT_FILES) == "init_files"
    assert str(ResourceType.KALI_ENV) == "kali_env"
    assert str(ResourceType.MEMORY) == "executor_agent_memory"
    assert str(ResourceType.MODEL) == "model"
    assert str(ResourceType.BOUNTY_SETUP) == "bounty_setup"
    assert str(ResourceType.REPO_SETUP) == "repo_setup"


def test_resource_type_key():
    assert ResourceType.DOCKER.key(workflow_id) == "docker"
    assert ResourceType.INIT_FILES.key(workflow_id) == "init_files"
    assert ResourceType.KALI_ENV.key(workflow_id) == f"kali_env_{workflow_id}"
    assert ResourceType.MEMORY.key(workflow_id) == "executor_agent_memory"
    assert ResourceType.MODEL.key(workflow_id) == "model"
    assert ResourceType.BOUNTY_SETUP.key(workflow_id) == "bounty_setup"
    assert ResourceType.REPO_SETUP.key(workflow_id) == "repo_setup"


def test_resource_type_get_class():
    assert ResourceType.DOCKER.get_class() == DockerResource
    assert ResourceType.INIT_FILES.get_class() == InitFilesResource
    assert ResourceType.KALI_ENV.get_class() == KaliEnvResource
    assert ResourceType.MEMORY.get_class() == MemoryResource
    assert ResourceType.MODEL.get_class() == ModelResource
    assert ResourceType.BOUNTY_SETUP.get_class() == BountySetupResource
    assert ResourceType.REPO_SETUP.get_class() == RepoSetupResource


# "uses" bounty_setup for import clarity
if None:
    bounty_setup
