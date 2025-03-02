import pytest
from resources.resource_manager import resource_dict
from resources.default_resource import AgentResourceManager, DefaultResource
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.memory_resource import MemoryResource
from resources.model_resource.model_resource import ModelResource
from resources.setup_resource import SetupResource
from tests.test_utils.bounty_setup_test_utils import workflow_id
from tests.test_utils.bounty_setup_test_utils import lunary_bounty_0_setup as bounty_setup



# Note: most of these tests assume that DOCKER exists in bounty_setup and MEMORY does not.

# Create a fake kali_env in the resource_dict
@pytest.fixture
def kali_resource_dict_fixture():
    kali_env_id = f"{str(DefaultResource.KALI_ENV)}_{workflow_id}"
    resource_dict.set(workflow_id, kali_env_id, 5)
    yield
    resource_dict.delete_items(workflow_id, kali_env_id)

def test_bind_resource_success(bounty_setup):
    am = AgentResourceManager()
    
    # Try to bind a resource and check if it works
    assert am.bind_resource(DefaultResource.DOCKER, workflow_id)
    assert isinstance(am.docker, DockerResource)


def test_bind_resource_not_found(bounty_setup):
    am = AgentResourceManager()
    
    # Attempt to bind a resource and expect it to fail
    assert not am.bind_resource(DefaultResource.MEMORY, workflow_id)
    assert am.docker is None  # Resource should not be set


def test_bind_resource_invalid_type(bounty_setup):
    am = AgentResourceManager()
    
    # Remove `docker` attribute to simulate an invalid resource type
    del am.docker

    # Attempt to bind a resource with an invalid type, which should raise a ValueError
    with pytest.raises(ValueError, match="Unexpected resource type"):
        am.bind_resource(DefaultResource.DOCKER, workflow_id)


def test_bind_resource_kali_env(kali_resource_dict_fixture):
    am = AgentResourceManager()
    
    # Bind KaliEnv resource with a specific workflow ID
    assert am.bind_resource(DefaultResource.KALI_ENV, workflow_id)
    assert am.kali_env == 5


def test_has_bound_true():
    am = AgentResourceManager()
    am.docker = "mock_resource"  # Simulate the resource being bound
    
    # Check if the resource is bound
    assert am.has_bound(DefaultResource.DOCKER)


def test_has_bound_false():
    am = AgentResourceManager()
    
    # Check if the resource is not bound
    assert not am.has_bound(DefaultResource.DOCKER)


def test_exists_found(bounty_setup):
    assert DefaultResource.DOCKER.exists(workflow_id)


def test_exists_not_found(bounty_setup):
    assert not DefaultResource.MEMORY.exists(workflow_id)

def test_default_resource_str():
    assert str(DefaultResource.DOCKER) == "docker"
    assert str(DefaultResource.INIT_FILES) == "init_files"
    assert str(DefaultResource.KALI_ENV) == "kali_env"
    assert str(DefaultResource.MEMORY) == "executor_agent_memory"
    assert str(DefaultResource.MODEL) == "model"
    assert str(DefaultResource.BOUNTY_RESOURCE) == "bounty_resource"
    assert str(DefaultResource.REPO_RESOURCE) == "repo_resource"

def test_default_resource_get_class():
    assert DefaultResource.DOCKER.get_class() == DockerResource
    assert DefaultResource.INIT_FILES.get_class() == InitFilesResource
    assert DefaultResource.KALI_ENV.get_class() == KaliEnvResource
    assert DefaultResource.MEMORY.get_class() == MemoryResource
    assert DefaultResource.MODEL.get_class() == ModelResource
    assert DefaultResource.BOUNTY_RESOURCE.get_class() == SetupResource
    assert DefaultResource.REPO_RESOURCE.get_class() == SetupResource


# "uses" bounty_setup for import clarity
if None:
    bounty_setup