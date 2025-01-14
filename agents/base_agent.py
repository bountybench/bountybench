from abc import ABC, abstractmethod
from typing import List, Set, Tuple, Type, Union

from resources.base_resource import BaseResource
from messages.message import Message
from messages.message_history import MessageHistory
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class ResourceNotInitializedError(Exception):
    """Raised when a resource is accessed before initialization."""
    pass

class AgentConfig(ABC):
    """Abstract base class for all agent configurations."""
    pass

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

    def __init__(self, agent_id: str, agent_config: AgentConfig):
        self._agent_id = agent_id
        self.agent_config = agent_config
        self.message_history = MessageHistory()
        self.target_host_address = getattr(agent_config, "target_host", "")

        logger.info(f"Initialized agent {self.agent_id}")

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
    async def run(self, messages: List[Message]) -> Message:
        """
        Execute the agent's main logic and produce a message.
        
        Args:
            messages: List of previous messages, if any.
        
        Returns:
            The agent's message after processing.
        """
        pass

    @abstractmethod
    def run(self, messages: List[Message]) -> Message:
        """
        Execute the agent's main logic and produce a message.
        
        Args:
            messages: List of previous messages, if any.
        
        Returns:
            The agent's message after processing.
        """
        pass

    @property
    def agent_id(self) -> str:
        return self._agent_id