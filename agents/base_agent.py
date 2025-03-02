from abc import ABC, abstractmethod
from typing import List, Set

from messages.agent_messages.agent_message import AgentMessage
from resources.resource_type import AgentResourceManager, ResourceType
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

    Resource entries are lists of DefaultResource enums
    """

    REQUIRED_RESOURCES: List[ResourceType] = []
    OPTIONAL_RESOURCES: List[ResourceType] = []
    ACCESSIBLE_RESOURCES: List[ResourceType] = []

    def __init__(self, agent_id: str, agent_config: AgentConfig):
        self._agent_id = agent_id
        self.agent_config = agent_config
        self.resources = AgentResourceManager()
        self.target_host_address = getattr(agent_config, "target_host", "")

        logger.info(f"Initialized agent {self.agent_id}")

    @classmethod
    def get_required_resources(cls) -> Set[str]:
        """Get the set of required resource attribute names."""
        return set(str(resource) for resource in cls.REQUIRED_RESOURCES)

    @classmethod
    def get_optional_resources(cls) -> Set[str]:
        """Get the set of optional resource attribute names."""
        return set(str(resource) for resource in cls.OPTIONAL_RESOURCES)
    
    @classmethod
    def get_accessible_resources(cls) -> Set[str]:
        """Get the set of optional resource attribute names."""
        return set(str(resource) for resource in cls.ACCESSIBLE_RESOURCES)

    @abstractmethod
    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
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
