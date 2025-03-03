from resources.resource_type import AgentResources, ResourceType
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.memory_resource import MemoryResource
from resources.model_resource.model_resource import ModelResource
from resources.setup_resource import SetupResource
from tests.agents.agent_test_utils import workflow_id


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

def test_default_resource_str():
    assert str(ResourceType.DOCKER) == "docker"
    assert str(ResourceType.INIT_FILES) == "init_files"
    assert str(ResourceType.KALI_ENV) == "kali_env"
    assert str(ResourceType.MEMORY) == "executor_agent_memory"
    assert str(ResourceType.MODEL) == "model"
    assert str(ResourceType.BOUNTY_RESOURCE) == "bounty_resource"
    assert str(ResourceType.REPO_RESOURCE) == "repo_resource"

def test_default_resource_get_class():
    assert ResourceType.DOCKER.get_class() == DockerResource
    assert ResourceType.INIT_FILES.get_class() == InitFilesResource
    assert ResourceType.KALI_ENV.get_class() == KaliEnvResource
    assert ResourceType.MEMORY.get_class() == MemoryResource
    assert ResourceType.MODEL.get_class() == ModelResource
    assert ResourceType.BOUNTY_RESOURCE.get_class() == SetupResource
    assert ResourceType.REPO_RESOURCE.get_class() == SetupResource
