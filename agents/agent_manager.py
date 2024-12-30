from typing import Dict, Type, Optional
from agents.base_agent import BaseAgent, AgentConfig
from resources.resource_manager import ResourceManager
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class AgentManager:
    """
    Manages the lifecycle of agents, ensuring that shared agents are not re-instantiated.
    """

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}  # agent_id -> agent_instance
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}  # agent_id -> agent_class
        self.resource_manager = ResourceManager()

    def get_or_create_agent(self, agent_id: str, agent_class: Type[BaseAgent], config: AgentConfig) -> BaseAgent:
        """
        Retrieve an existing agent by ID or create a new one if it doesn't exist.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_class (Type[BaseAgent]): The class of the agent to instantiate.
            config (AgentConfig): Configuration for the agent.

        Returns:
            BaseAgent: The existing or newly created agent instance.
        """
        if agent_id in self._agents:
            logger.debug(f"Agent '{agent_id}' already exists. Reusing the instance.")
            return self._agents[agent_id]
        
        # Create a new agent instance
        agent_instance = agent_class(agent_config=config, resource_manager=self.resource_manager)
        self._agents[agent_id] = agent_instance
        self._agent_classes[agent_id] = agent_class
        logger.info(f"Created and registered new agent '{agent_id}' of type '{agent_class.__name__}'.")
        return agent_instance

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Retrieve an agent by its ID.

        Args:
            agent_id (str): Unique identifier for the agent.

        Returns:
            Optional[BaseAgent]: The agent instance if it exists, else None.
        """
        return self._agents.get(agent_id, None)

    def register_agent(self, agent_id: str, agent_instance: BaseAgent):
        """
        Register an existing agent instance.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_instance (BaseAgent): The agent instance to register.
        """
        if agent_id in self._agents:
            logger.warning(f"Agent '{agent_id}' is already registered. Overwriting the existing instance.")
        self._agents[agent_id] = agent_instance
        self._agent_classes[agent_id] = type(agent_instance)
        logger.info(f"Registered agent '{agent_id}' of type '{type(agent_instance).__name__}'.")

    def remove_agent(self, agent_id: str):
        """
        Remove an agent from the manager.

        Args:
            agent_id (str): Unique identifier for the agent.
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            del self._agent_classes[agent_id]
            logger.info(f"Removed agent '{agent_id}' from the manager.")
        else:
            logger.warning(f"Attempted to remove non-existent agent '{agent_id}'.")