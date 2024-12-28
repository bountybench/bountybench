from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
from typing import List, Optional, Set, Tuple, Union

from resources.base_resource import BaseResource
from responses.failure_response import FailureResponse
from responses.response import Response
from responses.response_history import ResponseHistory
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class ResourceNotInitializedError(Exception):
    """Custom error for when a resource is accessed before initialization."""
    pass

@dataclass
class AgentConfig:
    id: str

class BaseAgent(ABC):
    """
    A base agent that automatically binds resources from a ResourceManager.
    Resource references can be declared in three lists:
      1) REQUIRED_RESOURCES  -> must exist, or KeyError is raised
      2) OPTIONAL_RESOURCES  -> if missing, attribute is omitted (no exception)
      3) ACCESSIBLE_RESOURCES -> must be subset of (required+optional).
    
    Each list entry can be:
      - A resource class (e.g. DockerResource)
      - A tuple (ResourceClass, "custom_attr_name")
    
    If only a class is given, `_generate_attr_name` is used to create a Python
    attribute name automatically (e.g. DockerResource -> "docker_resource").
    For optional resources, if not found, the attribute is *omitted* (not None).
    """

    # By default, these lists can be either a class or (class, "string").
    REQUIRED_RESOURCES: List[Union[type, Tuple[type, str]]] = []
    OPTIONAL_RESOURCES: List[Union[type, Tuple[type, str]]] = []
    ACCESSIBLE_RESOURCES: List[Union[type, Tuple[type, str]]] = []

    def __init__(self, agent_config: AgentConfig, resource_manager=None):
        """
        We do NOT fetch resources here. We'll do that in `register_resources()` 
        once we know they've been allocated by the ResourceManager.
        
        If `failure_detection=True` is passed, we wrap `run()` to detect repetitive responses.
        """
        object.__setattr__(self, '_initializing', True)
        object.__setattr__(self, '_resources_initialized', False)
        
        self.resource_manager = resource_manager
        self.response_history = ResponseHistory()
        self.agent_config = agent_config
        self.target_host_address = getattr(agent_config, "target_host", "")
        
        # Initialize all possible resource attributes to None
        for resource in self.REQUIRED_RESOURCES + self.OPTIONAL_RESOURCES:
            attr_name = self._entry_to_str(resource)
            object.__setattr__(self, attr_name, None)

        # Wrap the run method to ensure resources are initialized
        self._original_run = self.run
        self.run = self._wrapped_run
        
        object.__setattr__(self, '_initializing', False)
        # Optional: wrap the run(...) method for failure detection
        # if hasattr(self, "run") and kwargs.get("failure_detection", False):
        #     original_run = self.run

        #     def wrapped_run(responses: List[Response]) -> Response:
        #         new_response = original_run(responses)
        #         if self.response_history.is_repetitive(new_response):
        #             new_response = FailureResponse("Repetitive response detected")
        #         else:
        #             self.response_history.log(new_response)
        #         return new_response

        #     self.run = wrapped_run
        
    def _wrapped_run(self, responses: List[Response]) -> Response:
        if not self._resources_initialized:
            raise ResourceNotInitializedError("Resources have not been initialized. Call register_resources() before running the agent.")
        return self._original_run(responses)

    @classmethod
    def get_required_resources(cls) -> Set[str]:
        return set(cls._entry_to_str(resource) for resource in cls.REQUIRED_RESOURCES)

    def register_resources(self):
        """
        Binds required and optional resources from the ResourceManager.
        
        - For required resources: raises KeyError if missing.
        - For optional resources: if missing, we omit the attribute entirely.
        - Ensures ACCESSIBLE_RESOURCES is a subset of (REQUIRED_RESOURCES + OPTIONAL_RESOURCES).
        - Only sets attributes for resources in ACCESSIBLE_RESOURCES.
        """
        if not self.resource_manager:
            raise RuntimeError(f"Agent '{self.__class__.__name__}' has no resource_manager set; cannot fetch resources.")

        declared_resources = set(self.REQUIRED_RESOURCES) | set(self.OPTIONAL_RESOURCES)
        declared_attr_names = {self._entry_to_str(e) for e in declared_resources}
        accessible_attr_names = {self._entry_to_str(e) for e in self.ACCESSIBLE_RESOURCES}

        missing = accessible_attr_names - declared_attr_names
        if missing:
            raise ValueError(f"{self.__class__.__name__}: ACCESSIBLE_RESOURCES must be a subset of REQUIRED + OPTIONAL. Missing: {missing}")

        for entry in self.ACCESSIBLE_RESOURCES:
            attr_name = self._entry_to_str(entry)
            try:
                resource_obj = self.resource_manager.get_resource(attr_name)
                object.__setattr__(self, attr_name, resource_obj)
            except KeyError:
                if entry in self.REQUIRED_RESOURCES:
                    raise
                logger.warning(f"Optional resource '{attr_name}' not allocated. Attribute remains None.")

        object.__setattr__(self, '_resources_initialized', True)

    @staticmethod
    def _generate_attr_name(resource_cls: type) -> str:
        """
        Convert a Resource class into a snake_case attribute name.
        For instance, DockerResource -> "docker_resource",
        KaliEnvResource -> "kali_env", etc.
        """
        # 1) Remove trailing "Resource" if present
        name = resource_cls.__name__
        if name.endswith("Resource"):
            name = name[: -len("Resource")]  # remove the trailing "Resource"

        # 2) snake-case it
        words = re.findall(r'[A-Z][a-z]*|\d+', name)
        return '_'.join(word.lower() for word in words)

    @classmethod
    def _entry_to_str(cls, entry: Union[type, Tuple[type, str]]) -> str:
        """
        Return the attribute name used for subset-checking in ACCESSIBLE_RESOURCES.
        If we have (ResourceClass, "my_attr"), that's "my_attr".
        If we only have ResourceClass, we derive it automatically with _generate_attr_name.
        """
        if isinstance(entry, tuple):
            return entry[1]
        return cls._generate_attr_name(entry)


    def __getattribute__(self, name):
        # First, check if we're accessing one of the special attributes
        if name in ['_resources_initialized', '_initializing', 'get_required_resources', 'REQUIRED_RESOURCES']:
            return object.__getattribute__(self, name)
        
        # Now check if we're trying to access a required resource
        required_resources = object.__getattribute__(self, 'get_required_resources')()
        resources_initialized = object.__getattribute__(self, '_resources_initialized')
        
        if name in required_resources and not resources_initialized:
            raise ResourceNotInitializedError(f"Resource '{name}' has not been initialized. You must first initialize resources before accessing them.")
        
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name in ['_resources_initialized', '_initializing']:
            object.__setattr__(self, name, value)
            return
        
        initializing = object.__getattribute__(self, '_initializing')
        resources_initialized = object.__getattribute__(self, '_resources_initialized')
        required_resources = object.__getattribute__(self, 'get_required_resources')()
        
        if not initializing and name in required_resources and not resources_initialized:
            raise ResourceNotInitializedError(f"Cannot set resource '{name}'. Resources must be initialized through register_resources().")
        
        object.__setattr__(self, name, value)

    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        """
        Subclasses must implement how they handle input responses
        and produce a new response.
        """
        pass