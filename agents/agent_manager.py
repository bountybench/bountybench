from typing import Dict, List, Optional, Tuple, Type
from resources.resource_manager import resource_dict
from utils.logger import get_main_logger
from resources.model_resource.model_resource import ModelResource, ModelResourceConfig
from resources.default_resource import DefaultResource

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent, AgentConfig 

logger = get_main_logger(__name__)

class AgentManager:
    def __init__(self):
        self._agents: Dict[str, "BaseAgent"] = {}
        self._phase_agents: Dict[str, "BaseAgent"] = {}
        self._agent_configs: Dict[str, Tuple[Type["BaseAgent"], "AgentConfig"]] = {}
        self.resource_dict = resource_dict

    def register_agent(self, agent_id: str, agent_class: Type["BaseAgent"], agent_config: "AgentConfig"):
        """Register an agent with its class and configuration."""
        self._agent_configs[agent_id] = (agent_class, agent_config)

    def initialize_phase_agents(self, agent_configs: Dict[str, Tuple[Type["BaseAgent"], Optional["AgentConfig"]]]) -> List[Tuple[str, "BaseAgent"]]:
        """
        Initialize all agents for a phase in one batch operation.
        """
        logger.debug(f"Registered agents: {self._agent_configs.keys()}")
        
        initialized_agents = []
        self._phase_agents = {}
        
        # First register all agent configs
        for agent_id, (agent_class, agent_config) in agent_configs.items():
            self.register_agent(agent_id, agent_class, agent_config)
            
        # Then initialize all agents
        for agent_id in agent_configs.keys():
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                self._phase_agents[agent_id] = agent
                logger.debug(f"Agent {agent_id} already initialized, checking equivalence")
                
                # Check if existing agent matches configuration
                agent_class, agent_config = self._agent_configs[agent_id]
                if not self.is_agent_equivalent(agent_id, agent_class, agent_config):
                    raise ValueError(f"Agent {agent_id} exists with different configuration")
            else:
                logger.debug(f"Creating new agent {agent_id}")
                agent_class, agent_config = self._agent_configs[agent_id]
                
                try:
                    agent = self.create_agent(agent_id, agent_class, agent_config)
                    self._agents[agent_id] = agent
                    self._phase_agents[agent_id] = agent
                    logger.debug(f"Successfully created agent {agent_id}")
                except Exception as e:
                    logger.error(f"Failed to create agent {agent_id}: {str(e)}")
                    raise
                    
            initialized_agents.append((agent_id, self._agents[agent_id]))
            
        return initialized_agents
    
    def update_phase_agents_models(self, new_model: str):
        for agent_id in self._phase_agents:
            agent = self._phase_agents[agent_id]
            if str(DefaultResource.MODEL) in agent.get_accessible_resources():
                model_attr_name = str(DefaultResource.MODEL)
                if not hasattr(agent, model_attr_name):
                    raise AttributeError("Agent does not have a 'model' attribute")
                logger.info(f"Updating agent: {agent}, {agent.model.to_dict()}")
                resource_config = ModelResourceConfig.create(model=new_model)
                resource = ModelResource(model_attr_name, resource_config)
                setattr(agent, model_attr_name, resource)
                logger.info(f"Updated agent: {agent}, {agent.model.to_dict()}")

    def create_agent(self, agent_id: str, agent_class: Type["BaseAgent"], agent_config: "AgentConfig") -> "BaseAgent":
        """Create a new agent and bind resources to it."""
        agent = agent_class(agent_id, agent_config)
        self.validate_agent_required_resources(agent)
        return agent
    
    def validate_agent_required_resources(self, agent: "BaseAgent"):
        """Verify that required resources are set."""

        for resource_entry in agent.REQUIRED_RESOURCES:
            resource_name = str(resource_entry)
            resource = self.resource_dict.get(resource_name, None)
            if not resource:
                raise ValueError(f"Required resource {resource_entry.get_class().__name__} not found for agent {agent.__class__.__name__}")

    def is_agent_equivalent(self, agent_id: str, agent_class: Type["BaseAgent"], agent_config: "AgentConfig") -> bool:
        """Check if an agent with the given ID is equivalent to the provided class and config."""
        if agent_id not in self._agent_configs:
            return False
        registered_class, registered_config = self._agent_configs[agent_id]
        return registered_class == agent_class and registered_config == agent_config

    def get_agent(self, agent_id: str) -> "BaseAgent":
        """Retrieve an initialized agent by its ID."""
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not initialized")
        return self._agents[agent_id]
    
    def deallocate_all_agents(self):
        for agent_id, agent in self._agents.items():
            if hasattr(agent, 'cleanup'):
                agent.cleanup()
        self._agents.clear()
        self._phase_agents.clear()
        self._agent_configs.clear()
