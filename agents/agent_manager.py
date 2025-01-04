from typing import Dict, List, Tuple, Type
from agents.base_agent import BaseAgent, AgentConfig
from resources.resource_manager import ResourceManager
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class AgentManager:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_configs: Dict[str, Tuple[Type[BaseAgent], AgentConfig]] = {}

    def register_agent(self, agent_id: str, agent_class: Type[BaseAgent], agent_config: AgentConfig):
        """Register an agent with its class and configuration."""
        self._agent_configs[agent_id] = (agent_class, agent_config)

    '''
    def get_or_create_agent(self, agent_id: str, agent_class: Type[BaseAgent], agent_config: AgentConfig, resource_manager: ResourceManager) -> BaseAgent:
        """Get an existing agent or create a new one if it doesn't exist."""
        if agent_id in self._agents:
            existing_agent = self._agents[agent_id]
            if self.is_agent_equivalent(agent_id, agent_class, agent_config):
                return existing_agent
            else:
                raise ValueError(f"Agent '{agent_id}' already exists with different configuration")
        
        new_agent = agent_class(agent_config, resource_manager)
        self._agents[agent_id] = new_agent
        return new_agent
    '''


    def initialize_phase_agents(self, agent_configs: List[Tuple[str, AgentConfig]], agent_classes: List[Type[BaseAgent]]) -> List[Tuple[str, BaseAgent]]:
        """
        Initialize all agents for a phase in one batch operation.
        Similar to ResourceManager's initialize_phase_resources.
        """
        logger.debug(f"Registered agents: {self._agent_configs.keys()}")
        
        initialized_agents = []
        
        # First register all agent configs
        for agent_id, agent_config in agent_configs:
            agent_class = next(
                (ac for ac in agent_classes if isinstance(agent_config, ac.CONFIG_CLASS)),
                None
            )
            if agent_class is None:
                raise ValueError(f"No matching agent class for config type {type(agent_config)}")
                
            self.register_agent(agent_id, agent_class, agent_config)
            
        # Then initialize all agents
        for agent_id, _ in agent_configs:
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                logger.debug(f"Agent {agent_id} already initialized, checking equivalence")
                
                # Check if existing agent matches configuration
                agent_class, agent_config = self._agent_configs[agent_id]
                if not self.is_agent_equivalent(agent_id, agent_class, agent_config):
                    raise ValueError(f"Agent {agent_id} exists with different configuration")
            else:
                logger.debug(f"Creating new agent {agent_id}")
                agent_class, agent_config = self._agent_configs[agent_id]
                
                try:
                    agent = agent_class(agent_config)
                    self._agents[agent_id] = agent
                    logger.debug(f"Successfully created agent {agent_id}")
                except Exception as e:
                    logger.error(f"Failed to create agent {agent_id}: {str(e)}")
                    raise
                    
            initialized_agents.append((agent_id, self._agents[agent_id]))
            
        return initialized_agents
    
    def is_agent_equivalent(self, agent_id: str, agent_class: Type[BaseAgent], agent_config: AgentConfig) -> bool:
        """Check if an agent with the given ID is equivalent to the provided class and config."""
        if agent_id not in self._agent_configs:
            return False
        registered_class, registered_config = self._agent_configs[agent_id]
        return registered_class == agent_class and registered_config == agent_config

    def get_agent(self, agent_id: str) -> BaseAgent:
        """Retrieve an initialized agent by its ID."""
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not initialized")
        return self._agents[agent_id]