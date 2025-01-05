from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re
from typing import List, Optional, Set, Tuple, Type, Union

from resources.base_resource import BaseResource
from responses.failure_response import FailureResponse
from responses.response import Response
from responses.response_history import ResponseHistory
from utils.logger import get_main_logger
from utils.workflow_logger import workflow_logger

logger = get_main_logger(__name__)

class ResourceNotInitializedError(Exception):
    """Raised when a resource is accessed before initialization."""
    pass

@dataclass
class AgentConfig:
    id: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        if self.id is None:
            self.id = self.__class__.__name__

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

    def __init__(self, agent_config: AgentConfig):
        self.agent_config = agent_config
        self.response_history = ResponseHistory()
        self.target_host_address = getattr(agent_config, "target_host", "")

        logger.info(f"Initialized agent {agent_config.id}")
        
        workflow_logger.add_agent(self.agent_config.id, self)

    @staticmethod
    def _parse_resource_entry(entry: Union[Type[BaseResource], Tuple[Type[BaseResource], str]]) -> Tuple[Type[BaseResource], str]:
        if isinstance(entry, tuple):
            return entry
        return entry, entry.__name__.lower()

    @classmethod
    def get_required_resources(cls) -> Set[str]:
        """Get the set of required resource attribute names."""
        return set(cls._parse_resource_entry(resource)[1] for resource in cls.REQUIRED_RESOURCES)

    @classmethod
    def get_optional_resources(cls) -> Set[str]:
        """Get the set of optional resource attribute names."""
        return set(cls._parse_resource_entry(resource)[1] for resource in cls.OPTIONAL_RESOURCES)

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