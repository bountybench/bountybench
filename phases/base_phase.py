from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent
from phase_messages.phase_message import PhaseMessage
from resources.base_resource import BaseResource
from messages.message import Message
from utils.logger import get_main_logger
from utils.workflow_logger import workflow_logger

logger = get_main_logger(__name__)


if TYPE_CHECKING:
    from workflows.base_workflow import BaseWorkflow

@dataclass
class PhaseConfig:
    phase_name: str
    agent_configs: List[Tuple[str, 'AgentConfig']] = field(default_factory=list)
    max_iterations: int = 10
    interactive: bool = False
    phase_idx: Optional[int] = None
    initial_prompt: Optional[str] = None

    @classmethod
    def from_phase(cls, phase_instance: 'BasePhase', **kwargs):
        config = cls(
            phase_name=phase_instance.name,
            agent_configs=phase_instance.define_agents(),
            **kwargs
        )
        return config
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Type
from agents.base_agent import AgentConfig, BaseAgent
from resources.base_resource import BaseResource, BaseResourceConfig

class BasePhase(ABC):
    AGENT_CLASSES: List[Type[BaseAgent]] = []

    def __init__(self, workflow: 'BaseWorkflow', **kwargs):
        self.workflow = workflow
        self.phase_config = PhaseConfig.from_phase(self, **kwargs)

        self.agent_manager = self.workflow.agent_manager
        self.resource_manager = self.workflow.resource_manager
        self.agents: List[Tuple[str, BaseAgent]] = []
        self.initial_message = kwargs.get("initial_prompt", None)
        self._done = False
        self.phase_summary: Optional[str] = None
        self.iteration_count = 0
        self.current_agent_index = 0

    @abstractmethod
    def define_resources(self) -> Dict[str, Tuple[Type[BaseResource], Optional[BaseResourceConfig]]]:
        """
        Define the resources required for this phase.
        
        Returns:
            Dict[str, Tuple[Type[BaseResource], Optional[BaseResourceConfig]]]: 
            A dictionary mapping resource IDs to their class and config.
        """
        pass

    @abstractmethod
    def define_agents(self) -> List[Tuple[str, AgentConfig]]:
        """
        Define the agents required for this phase.
        
        Returns:
            List[Tuple[str, AgentConfig]]: A list of tuples containing agent IDs and their configs.
        """
        pass


    def get_phase_resources(self):
        phase_resources = {}
        for agent_class in self.AGENT_CLASSES:
            phase_resources.update(agent_class.REQUIRED_RESOURCES)
        return phase_resources

    def __rshift__(self, other):
        if isinstance(other, BasePhase):
            if self not in self.workflow._phase_graph:
                self.workflow.register_phase(self)
            if other not in self.workflow._phase_graph:
                self.workflow.register_phase(other)
            self.workflow._phase_graph[self].append(other)
        return other


    @classmethod
    def get_required_resources(cls) -> Set[str]:
        resources = set()
        for agent_cls in cls.AGENT_CLASSES:
            resources.update(agent_cls.get_required_resources())
        return resources

    def setup(self):
        """
        Initialize and register resources and agents for the phase.
        """
        logger.debug(f"Entering setup for {self.name}")
        
        # 1. Define and register resources
        resource_configs = self.define_resources()
        for resource_id, (resource_class, resource_config) in resource_configs.items():
            if not self.resource_manager.is_resource_equivalent(resource_id, resource_class, resource_config):
                self.resource_manager.register_resource(resource_id, resource_class, resource_config)
        
        # 2. Initialize phase resources
        self.resource_manager.initialize_phase_resources(self.phase_config.phase_idx, resource_configs.keys())
        
        # 3. Define and register agents
        agent_configs = self.define_agents()
        '''
        for agent_id, agent_config in agent_configs:
            agent_class = next((ac for ac in self.AGENT_CLASSES if isinstance(agent_config, ac.CONFIG_CLASS)), None)
            if agent_class is None:
                raise ValueError(f"No matching agent class found for config type {type(agent_config)}")
            
            try:
                #4. Initialize phase agent(s)
                agent = self.agent_manager.get_or_create_agent(agent_id, agent_class, agent_config, self.resource_manager)
                self.agents.append((agent_id, agent))
            except Exception as e:
                logger.error(f"Error creating agent {agent_id}: {str(e)}")
                raise
        '''

        self.agent_manager.initialize_phase_agents(agent_configs, self.AGENT_CLASSES)
        self.agents = list(self.agent_manager._agents.items())

        
        logger.debug(f"Completed setup for {self.name}")

    def deallocate_resources(self):
        """
        Deallocate resources after the phase is completed.
        """
        try:
            self.resource_manager.deallocate_phase_resources(self.phase_config.phase_idx)
            logger.info(f"Phase {self.phase_config.phase_idx} ({self.phase_config.phase_name}) resources deallocated.")
        except Exception as e:
            logger.error(f"Failed to deallocate resources for phase {self.phase_config.phase_idx}: {e}")
            raise

    
    def run_phase(self, prev_phase_message: PhaseMessage) -> PhaseMessage:
        """
        Execute the phase by running its iterations.

        Args:
            phase_message (PhaseMessage): The message from the previous phase.

        Returns:
            PhaseMessage: The message of the current phase.
        """
        logger.debug(f"Entering run_phase for phase {self.phase_config.phase_idx} ({self.phase_config.phase_name})")

        last_agent_message = prev_phase_message.agent_messages[-1]
        curr_phase_message = PhaseMessage(agent_messages=[])

        # 1) Start phase context
        with workflow_logger.phase(self) as phase_ctx:
            for iteration_num in range(1, self.phase_config.max_iterations + 1):
                if curr_phase_message.complete:
                    break

                agent_id, agent_instance = self._get_current_agent()

                if last_agent_message:
                    print(f"Last output was {last_agent_message.message}")
                else:
                    print("No last output")

                # 2) Start iteration context in the logger
                with phase_ctx.iteration(iteration_num, agent_id, last_agent_message) as iteration_ctx:
                    message = self.run_one_iteration(
                        phase_message=curr_phase_message,
                        agent_instance=agent_instance,
                        previous_output=last_agent_message,
                    )
                    iteration_ctx.set_output(message)

                if curr_phase_message.complete:
                    break

                last_agent_message = curr_phase_message.agent_messages[-1]

                # Increment the iteration count
                self.iteration_count += 1
                self.current_agent_index += 1

        if not self.phase_summary:
            self._set_phase_summary("completed_max_phase_iterations")

        # Deallocate resources after completing iterations
        self.deallocate_resources()

        return curr_phase_message

    def _get_current_agent(self) -> Tuple[str, BaseAgent]:
        """Retrieve the next agent in a round-robin fashion."""
        agent = self.agents[self.current_agent_index % len(self.agents)]
        self.current_agent_index += 1
        return agent

    def _set_phase_summary(self, summary: str):
        """Allows a subclass to record a short message describing the phase outcome."""
        self.phase_summary = summary

    @abstractmethod
    def define_agents(self) -> List[Tuple[str, AgentConfig]]:
        """
        Provide agent configurations for the phase.

        Returns:
            List[Tuple[str, AgentConfig]]: List of (agent_id, AgentConfig) tuples.
        """
        pass
    
    @abstractmethod
    def define_resources(self)-> Dict[str, Tuple[Type['BaseResource'], Any]]: 
        pass

    @abstractmethod
    def run_one_iteration(
        self, phase_message: PhaseMessage, agent_instance: Any, previous_output: Optional[Message]
    ) -> Message:
        """
        Run a single iteration of the phase.

        Args:
            agent_instance (BaseAgent): The agent to run.
            previous_output (Optional[Message]): The output from the previous iteration.

        Returns:
            Message: The message from the agent.
        """
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__