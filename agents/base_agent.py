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
    """Raised when a resource is accessed before initialization."""
    pass

@dataclass
class AgentConfig:
    id: str

class BaseAgent(ABC):
    """
    Abstract base class for agents with managed resources.

    Resources are declared in three lists:
    - REQUIRED_RESOURCES: Must exist, or KeyError is raised
    - OPTIONAL_RESOURCES: Used if available, no exception if missing
    - ACCESSIBLE_RESOURCES: Subset of required and optional that will be bound as attributes

    Resource entries can be:
    - A resource class (e.g., DockerResource)
    - A tuple (ResourceClass, "custom_attr_name")
    """

    REQUIRED_RESOURCES: List[Union[type, Tuple[type, str]]] = []
    OPTIONAL_RESOURCES: List[Union[type, Tuple[type, str]]] = []
    ACCESSIBLE_RESOURCES: List[Union[type, Tuple[type, str]]] = []

    def __init__(self, agent_config: AgentConfig, resource_manager=None):
        """
        Initialize the agent without fetching resources.
        Resources are initialized later via register_resources().
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
        """Ensure resources are initialized before running the agent."""
        if not self._resources_initialized:
            raise ResourceNotInitializedError("Resources not initialized. Call register_resources() first.")
        return self._original_run(responses)

    @classmethod
    def get_required_resources(cls) -> Set[str]:
        """Get the set of required resource attribute names."""
        return set(cls._entry_to_str(resource) for resource in cls.REQUIRED_RESOURCES)

    def register_resources(self):
        """
        Bind resources from the ResourceManager to the agent.
        
        Raises:
            RuntimeError: If ResourceManager is not set.
            ValueError: If ACCESSIBLE_RESOURCES is not a subset of (REQUIRED + OPTIONAL).
            KeyError: If a required resource is missing.
        """
        if not self.resource_manager:
            raise RuntimeError(f"Agent '{self.__class__.__name__}' has no ResourceManager set.")

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
        """Generate a snake_case attribute name from a resource class name."""
        name = resource_cls.__name__
        if name.endswith("Resource"):
            name = name[:-len("Resource")]
        words = re.findall(r'[A-Z][a-z]*|\d+', name)
        return '_'.join(word.lower() for word in words)

    @classmethod
    def _entry_to_str(cls, entry: Union[type, Tuple[type, str]]) -> str:
        """Get the attribute name for a resource entry."""
        return entry[1] if isinstance(entry, tuple) else cls._generate_attr_name(entry)

    def __getattribute__(self, name):
        """Custom attribute access to enforce resource initialization."""
        if name in ['_resources_initialized', '_initializing', 'get_required_resources', 'REQUIRED_RESOURCES']:
            return object.__getattribute__(self, name)
        
        required_resources = object.__getattribute__(self, 'get_required_resources')()
        resources_initialized = object.__getattribute__(self, '_resources_initialized')
        
        if name in required_resources and not resources_initialized:
            raise ResourceNotInitializedError(f"Resource '{name}' not initialized. Call register_resources() first.")
        
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        """Custom attribute setting to enforce resource initialization."""
        if name in ['_resources_initialized', '_initializing']:
            object.__setattr__(self, name, value)
            return
        
        initializing = object.__getattribute__(self, '_initializing')
        resources_initialized = object.__getattribute__(self, '_resources_initialized')
        required_resources = object.__getattribute__(self, 'get_required_resources')()
        
        if not initializing and name in required_resources and not resources_initialized:
            raise ResourceNotInitializedError(f"Cannot set resource '{name}'. Call register_resources() first.")
        
        object.__setattr__(self, name, value)

    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        """
        Execute the agent's main logic and produce a response.
        
        Args:
            responses: List of previous responses, if any.
        
        Returns:
            The agent's response after processing.
        """
        pass