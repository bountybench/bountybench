from enum import Enum
from typing import TYPE_CHECKING, Type

from resources.resource_manager import resource_dict

from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.memory_resource import MemoryResource
from resources.model_resource.model_resource import ModelResource
from resources.setup_resource import SetupResource

if TYPE_CHECKING:
    from resources.base_resource import BaseResource

class _Resource:
    def __init__(self, resource_id: str, resource_class: Type["BaseResource"]):
        self.resource_id = resource_id
        self.resource_class = resource_class

    def __str__(self):
        return self.resource_id

    def get_class(self):
        return self.resource_class

class DefaultResource(Enum):
    DOCKER = _Resource("docker", DockerResource)
    INIT_FILES = _Resource("init_files", InitFilesResource)
    KALI_ENV = _Resource("kali_env", KaliEnvResource)
    MEMORY = _Resource("executor_agent_memory", MemoryResource)
    MODEL = _Resource("model", ModelResource)
    BOUNTY_RESOURCE = _Resource("bounty_resource", SetupResource)
    REPO_RESOURCE = _Resource("repo_resource", SetupResource)

    def __str__(self):
        return str(self.value)

    def get_class(self):
        return self.value.get_class()
    
class AgentResourceManager:
    """
    Class which agents rely on to bind their resources.
    Attribute names match str(DefaultResource).
    
    """
    def __init__(self):
        self.docker = None
        self.init_files = None
        self.kali_env = None
        self.executor_agent_memory = None
        self.model = None
        self.bounty_resource = None
        self.repo_resource=  None

    def has_attr(self, resource:DefaultResource) -> bool:
        return hasattr(self, str(resource))

    def has_bound(self, resource: DefaultResource) -> bool:
        return self.has_attr(resource) and getattr(self, str(resource)) is not None

    def bind_resource(self, resource: DefaultResource, workflow_id: str) -> bool:
        """ Binds resource for agent access. Returns False if resource does not exist and True otherwise. """
        resource = None
        if resource_dict.contains(workflow_id, str(resource)):
            resource = resource_dict.get(workflow_id, str(resource))

        if resource:
            if self.has_attr(resource):
                setattr(self, str(resource), resource)
                return True
            else:
                raise ValueError(f"Unexpected resource type: {resource}")
        return False
