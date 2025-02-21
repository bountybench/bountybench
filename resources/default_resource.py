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
    from agents.base_agent import BaseAgent

class _Resource:
    def __init__(self, resource_id: str, resource_class: Type["BaseResource"]):
        self.resource_id = resource_id
        self.resource_class = resource_class
    
    def __str__(self):
        return self.resource_id
    
    def init(self):
        raise NotImplementedError

    def get_resource(self, agent: "BaseAgent"):
        if str(self) in agent.get_accessible_resources():
            # raise KeyError(f"Resource {self.resource_id} not registered/initialized by resource manager.")
            return resource_dict.get(self.resource_id, None)
        raise PermissionError(f"{agent.agent_id} tried to access inaccessible resource.")
    
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

    def get_resource(self, agent: "BaseAgent"):
        return self.value.get_resource(agent)
    
    def get_class(self):
        return self.value.get_class()


"""
DENIS' TODO
tests/agents/test_base_agent.py
add test for setup_resources in patch/exploit. and fix them
TODO: Remove duplicate functions in agent classes.
TODO: Patch/Exploit kali env
"""

