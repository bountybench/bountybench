from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, TypeVar

from messages.agent_messages.agent_message import AgentMessage
from resources.resource_type import AgentResources, ResourceType
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class IterationFailure(Exception):
    """Raised when an iteration fails, but want to propagate a partially complete AgentMessage to the phase."""

    def __init__(self, message: str, agent_message: Optional[AgentMessage] = None):
        super().__init__(message)
        self.agent_message = agent_message


class ResourceNotInitializedError(Exception):
    """Raised when a resource is accessed before initialization."""

    pass


class AgentConfig(ABC):
    """Abstract base class for all agent configurations."""

    pass


T = TypeVar("T", bound="BaseAgent")


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
        self.resources = AgentResources()
        self.target_host_address = getattr(agent_config, "target_host", "")

        logger.info(f"Initialized agent {self.agent_id}")

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

    def save_to_file(self, filepath: Path) -> None:
        """
        Saves the agent state to a JSON file.
        """
        import json

        state = self.to_dict()
        filepath.write_text(json.dumps(state, indent=2))

    @classmethod
    def load_from_file(cls, filepath: Path, **kwargs) -> T:
        """
        Loads an agent state from a JSON file.
        """
        import json

        data = json.loads(filepath.read_text())
        return cls.from_dict(data, **kwargs)
