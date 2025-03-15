from typing import Dict, List, Optional, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent
from resources.model_resource.model_resource import ModelResource, ModelResourceConfig
from resources.resource_manager import resource_dict
from resources.resource_type import ResourceType
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class AgentManager:
    def __init__(self, workflow_id: str):
        self._agents: Dict[str, BaseAgent] = {}
        self._phase_agents: Dict[str, BaseAgent] = {}
        self._agent_configs: Dict[str, Tuple[Type[BaseAgent], AgentConfig]] = {}
        self.workflow_id = workflow_id
        self.resource_dict = resource_dict

    def register_agent(
        self, agent_id: str, agent_class: Type[BaseAgent], agent_config: AgentConfig
    ):
        """Register an agent with its class and configuration."""
        self._agent_configs[agent_id] = (agent_class, agent_config)

    def initialize_phase_agents(
        self, agent_configs: Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]
    ) -> List[Tuple[str, BaseAgent]]:
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
                logger.debug(
                    f"Agent {agent_id} already initialized, checking equivalence"
                )

                # Check if existing agent matches configuration
                agent_class, agent_config = self._agent_configs[agent_id]
                if not self.is_agent_equivalent(agent_id, agent_class, agent_config):
                    raise ValueError(
                        f"Agent {agent_id} exists with different configuration"
                    )
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
            if ResourceType.MODEL in agent.ACCESSIBLE_RESOURCES:
                if not agent.resources.has_bound(ResourceType.MODEL):
                    raise AttributeError("Agent does not have a 'model' attribute")
                logger.info(
                    f"Updating agent: {agent}, {agent.resources.model.to_dict()}"
                )
                # If a model resource exist, only need to update the model name
                # resource_manager already handles resource registration
                if agent.resources.model:
                    existing_model_name = agent.resources.model.model
                    logger.info(
                        f"Updating agent {agent_id} from {existing_model_name} to {new_model}"
                    )
                    agent.resources.model.model = new_model
                else:
                    resource_config = ModelResourceConfig.create(model=new_model)
                    resource = ModelResource("model", resource_config)
                    agent.resources.model = resource

                logger.info(
                    f"Updated agent: {agent}, {agent.resources.model.to_dict()}"
                )

    def update_phase_agents_mock_model(self, use_mock_model: bool):
        """
        Ensures all agents update their ModelResource with the new `use_mock_model` setting.
        """
        for agent_id, agent in self._phase_agents.items():
            if ResourceType.MODEL in agent.ACCESSIBLE_RESOURCES:
                if not agent.resources.has_bound(ResourceType.MODEL):
                    raise AttributeError("Agent does not have a 'model' attribute")

                if agent.resources.model:
                    existing_model_name = agent.resources.model.model
                    logger.info(
                        f"Updating agent {agent_id} to use_mock_model={use_mock_model}"
                    )
                    agent.resources.model.use_mock_model = use_mock_model
                else:
                    resource_config = ModelResourceConfig.create(
                        model=existing_model_name, use_mock_model=use_mock_model
                    )
                    resource = ModelResource("model", resource_config)
                    agent.resources.model = resource

                logger.info(
                    f"Agent {agent_id} updated: {agent.resources.model.to_dict()}"
                )

    def create_agent(
        self, agent_id: str, agent_class: Type[BaseAgent], agent_config: AgentConfig
    ) -> BaseAgent:
        """Create a new agent and bind resources to it."""
        agent = agent_class(agent_id, agent_config)
        self.bind_resources_to_agent(agent)
        return agent

    def validate_required_resources_exist(self, agent: BaseAgent):
        """Checks to make sure that agent's required resources are initialized."""
        for resource_entry in agent.REQUIRED_RESOURCES:
            if not resource_entry.exists(self.workflow_id):
                raise ValueError(
                    f"Required resource {str(resource_entry)} for agent {agent.__class__.__name__} not set for workflow {self.workflow_id} for agent {agent.__class__.__name__}"
                )

    def bind_resources_to_agent(self, agent: BaseAgent):
        """Bind accessible resources to the agent."""

        for resource_entry in agent.ACCESSIBLE_RESOURCES:
            resource = None

            # KaliEnv has a separate ID {kali_env_{workflow_id}}. We still want to access it via self.resources.kali_env.
            resource_name = resource_entry.key(self.workflow_id)
            if self.resource_dict.contains(self.workflow_id, resource_name):
                resource = self.resource_dict.get(self.workflow_id, resource_name)

            if resource:
                if agent.resources.has_attr(resource_entry):
                    setattr(agent.resources, str(resource_entry), resource)
                else:
                    raise ValueError(
                        f"Required resource {str(resource_entry)} not found for agent {agent.__class__.__name__}"
                    )
            else:
                if resource_entry in agent.REQUIRED_RESOURCES:
                    raise ValueError(
                        f"Accessible, required resource {str(resource_entry)} missing for agent {agent.__class__.__name__}"
                    )

    def is_agent_equivalent(
        self, agent_id: str, agent_class: Type[BaseAgent], agent_config: AgentConfig
    ) -> bool:
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

    def deallocate_all_agents(self):
        for agent_id, agent in self._agents.items():
            if hasattr(agent, "cleanup"):
                agent.cleanup()
        self._agents.clear()
        self._phase_agents.clear()
        self._agent_configs.clear()
