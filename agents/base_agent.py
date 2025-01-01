from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
from typing import List, Optional, Set, Tuple, Type, Union

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
        # Set these attributes first
        object.__setattr__(self, '_initializing', True)
        object.__setattr__(self, '_resources_initialized', False)
        object.__setattr__(self, '_required_resources', set())
        object.__setattr__(self, '_optional_resources', set())

        # Now compute the resources
        object.__setattr__(self, '_required_resources', self._compute_required_resources())
        object.__setattr__(self, '_optional_resources', self._compute_optional_resources())
        
        self.resource_manager = resource_manager
        self.response_history = ResponseHistory()
        self.agent_config = agent_config
        self.target_host_address = getattr(agent_config, "target_host", "")
        self._resources = {}
        
        # Initialize all possible resource attributes to None
        for resource in self.REQUIRED_RESOURCES + self.OPTIONAL_RESOURCES:
            attr_name = self._entry_to_str(resource)
            object.__setattr__(self, attr_name, None)

        # Wrap the run method to ensure resources are initialized
        self._original_run = self.run
        self.run = self._wrapped_run
        
        #object.__setattr__(self, '_initializing', False)
        logger.info(f"Initialized agent {agent_config.id}")
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

    def _compute_required_resources(self):
        return set(self._entry_to_str(resource) for resource in self.REQUIRED_RESOURCES)

    def _compute_optional_resources(self):
        return set(self._entry_to_str(resource) for resource in self.OPTIONAL_RESOURCES)

    def _wrapped_run(self, responses: List[Response]) -> Response:
        """Ensure resources are initialized before running the agent."""
        print(f"Debugging: _wrapped_run called for {self.__class__.__name__}")
        print(f"Debugging: _resources_initialized = {self._resources_initialized}")
        if not self._resources_initialized:
            raise ResourceNotInitializedError("Resources not initialized. Call register_resources() first.")
        return self._original_run(responses)

    @classmethod
    def get_required_resources(cls) -> Set[Type[BaseResource]]:
        """Get the set of required resource classes."""
        return set(
            resource if isinstance(resource, type) else resource[0]
            for resource in cls.REQUIRED_RESOURCES + cls.OPTIONAL_RESOURCES
        )

    def register_resources(self, resource_manager):
            """Register resources using the provided resource manager."""
            print(f"Debugging: Entering register_resources for {self.__class__.__name__}")
            
            for resource in self.ACCESSIBLE_RESOURCES:
                if isinstance(resource, tuple):
                    resource_class, attr_name = resource
                else:
                    resource_class = resource
                    attr_name = resource_class.__name__.lower().replace('resource', '')

                try:
                    resource_obj = resource_manager.get_resource(attr_name)
                    setattr(self, attr_name, resource_obj)
                except KeyError:
                    if resource in self.REQUIRED_RESOURCES:
                        raise ValueError(f"Required resource '{attr_name}' not initialized for {self.__class__.__name__}")
                    else:
                        setattr(self, attr_name, None)

            self._resources_initialized = True
            print(f"Debugging: Exiting register_resources for {self.__class__.__name__}")
   
        
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
        if name in ['_resources_initialized', '_initializing', '_required_resources', '_optional_resources']:
            return object.__getattribute__(self, name)
        
        resources_initialized = object.__getattribute__(self, '_resources_initialized')
        if not resources_initialized:
            required_resources = object.__getattribute__(self, '_required_resources')
            optional_resources = object.__getattribute__(self, '_optional_resources')
            
            if name in required_resources:
                if name in optional_resources:
                    return None
                raise ResourceNotInitializedError(f"Resource '{name}' not initialized. Call register_resources() first.")
        
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        """Custom attribute setting to enforce resource initialization."""
        if name in ['_resources_initialized', '_initializing']:
            object.__setattr__(self, name, value)
            return
        
        initializing = object.__getattribute__(self, '_initializing')
        resources_initialized = object.__getattribute__(self, '_resources_initialized')
        
        if not initializing and not resources_initialized:
            required_resources = object.__getattribute__(self, '_required_resources')
            optional_resources = object.__getattribute__(self, '_optional_resources')
            
            if name in required_resources and name not in optional_resources:
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