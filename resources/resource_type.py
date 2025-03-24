from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional, Type

from resources.bounty_setup_resource import BountySetupResource
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.memory_resource import MemoryResource
from resources.model_resource.model_resource import ModelResource
from resources.repo_setup_resource import RepoSetupResource
from resources.resource_manager import resource_dict

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


class ResourceType(Enum):
    DOCKER = _Resource("docker", DockerResource)
    INIT_FILES = _Resource("init_files", InitFilesResource)
    KALI_ENV = _Resource("kali_env", KaliEnvResource)
    MEMORY = _Resource("executor_agent_memory", MemoryResource)
    MODEL = _Resource("model", ModelResource)
    BOUNTY_SETUP = _Resource("bounty_setup", BountySetupResource)
    REPO_SETUP = _Resource("repo_setup", RepoSetupResource)

    def __str__(self):
        return str(self.value)

    def key(self, workflow_id: str):
        """Gets resource ID. Same as str(self) except for KALI_ENV."""
        return (
            str(self) if self != ResourceType.KALI_ENV else f"{str(self)}_{workflow_id}"
        )

    def get_class(self):
        return self.value.get_class()

    def exists(self, workflow_id: str) -> bool:
        return resource_dict.contains(
            workflow_id=workflow_id,
            resource_id=str(self),
        )


class AgentResources:
    """
    Class which agents rely on to access their resources.
    Attribute names match str(ResourceType).

    This is a container. The actual resources are defined in the define_resources() method of each phase.
    e.g. see ../phases/patch_phase.py
    """

    def __init__(self):
        self.docker: Optional[Literal[ResourceType.DOCKER]] = None
        self.init_files: Optional[Literal[ResourceType.INIT_FILES]] = None
        self.kali_env: Optional[Literal[ResourceType.KALI_ENV]] = None
        self.executor_agent_memory: Optional[Literal[ResourceType.MEMORY]] = None
        self.model: Optional[Literal[ResourceType.MODEL]] = None
        self.bounty_setup: Optional[Literal[ResourceType.BOUNTY_SETUP]] = None
        self.repo_setup: Optional[Literal[ResourceType.REPO_SETUP]] = None

    def has_attr(self, resource: ResourceType) -> bool:
        return hasattr(self, str(resource))

    def has_bound(self, resource: ResourceType) -> bool:
        return self.has_attr(resource) and getattr(self, str(resource)) is not None
