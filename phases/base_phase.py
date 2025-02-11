from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import wraps
import os
import subprocess
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.message_utils import log_message
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from resources.base_resource import BaseResource, BaseResourceConfig
from messages.message import Message
from utils.logger import get_main_logger
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Type
from agents.base_agent import AgentConfig, BaseAgent
from resources.base_resource import BaseResource, BaseResourceConfig

logger = get_main_logger(__name__)


if TYPE_CHECKING:
    from workflows.base_workflow import BaseWorkflow

@dataclass
class PhaseConfig:
    phase_name: str
    agent_configs: List[Tuple[str, 'AgentConfig']] = field(default_factory=list)
    max_iterations: int = field(default=10)
    interactive: bool = False
    phase_idx: Optional[int] = None

    @classmethod
    def from_phase(cls, phase_instance: 'BasePhase', **kwargs):
        # Filter out kwargs that are not attributes of PhaseConfig
        valid_kwargs = {k: v for k, v in kwargs.items() if k in cls.__annotations__}
        
        config = cls(
            phase_name=phase_instance.name,
            agent_configs=phase_instance.define_agents(),
            **valid_kwargs
        )
        return config
    
class BasePhase(ABC):
    AGENT_CLASSES: List[Type[BaseAgent]] = []

    def __init__(self, workflow: 'BaseWorkflow', **kwargs):
        self.workflow = workflow
        self.phase_config = PhaseConfig.from_phase(self, **kwargs)

        self.agent_manager = self.workflow.agent_manager
        self.resource_manager = self.workflow.resource_manager
        self.agents: List[Tuple[str, BaseAgent]] = []
        self.params = kwargs
        self._done = False
        self.iteration_count = 0
        self.current_agent_index = 0
        self._last_agent_message = None

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
    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        """
        Define the agents required for this phase.
        
        Returns:
            Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]: 
            A dictionary mapping agent IDs to their class and config.
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
        logger.info(f"Resources for phase {self.name} initialized")
        # 3. Define and register agents
        agent_configs = self.define_agents()

        self.agent_manager.initialize_phase_agents(agent_configs)
        logger.info(f"Agents for phase {self.name} initialized")
        self.agents = list(self.agent_manager._phase_agents.items())

        logger.info(f"Completed setup for {self.name}")

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

    async def run_phase(self, workflow_message: WorkflowMessage, prev_phase_message: PhaseMessage) -> PhaseMessage:
        """
        Execute the phase by running its iterations.

        Args:
            phase_message (PhaseMessage): The message from the previous phase.

        Returns:
            PhaseMessage: The message of the current phase.
        """
        logger.info(f"running Phase {self.name} starting at iteration {self.iteration_count}")

        if self.iteration_count == 0:           
            self._phase_message = PhaseMessage(phase_id=self.name, prev=prev_phase_message)
            workflow_message.add_phase_message(self._phase_message)

            if prev_phase_message and len(prev_phase_message.agent_messages) > 0:
                self._last_agent_message = prev_phase_message.agent_messages[-1]
            else:
                logger.info(f"Adding initial prompt to phase")
                if self.params.get("task_dir"):
                    codebase_structure = subprocess.run(["tree", "-L", "4"], cwd=os.path.join(self.params.get("task_dir"), "tmp"), capture_output=True, text=True).stdout
                    self.params["codebase"] = "$ tree -L 4\n" + codebase_structure
                self._last_agent_message = AgentMessage(
                    agent_id="system",
                    message=self.params.get("initial_prompt").format(**self.params),
                )
                self._phase_message.add_agent_message(self._last_agent_message)
            self.iteration_count += 1

        start_count = self.iteration_count
        # Start the iteration at the current count
        for iteration_num in range(start_count, self.phase_config.max_iterations + 1):
            if self._phase_message.complete:
                break

            if self.phase_config.interactive:
                if hasattr(self.workflow, 'next_iteration_event'):
                    logger.info("Waiting for 'next' signal ...")
                    self.workflow.next_iteration_event.clear()
                    await self.workflow.next_iteration_event.wait()
                else:
                    logger.warning("Interactive mode is set, but workflow doesn't have next_iteration_event")

            agent_id, agent_instance = self._get_current_agent()
            logger.info(f"Running iteration {iteration_num} of {self.name} with {agent_id}")

            while self._last_agent_message.version_next:
                self._last_agent_message = self._last_agent_message.version_next
                
            message = await self.run_one_iteration(
                phase_message=self._phase_message,
                agent_instance=agent_instance,
                previous_output=self._last_agent_message,
            )
            self._phase_message.add_agent_message(message)

            logger.info(f"Finished iteration {iteration_num} of {self.name} with {agent_id}")
            if self._phase_message.complete:
                break

            self._last_agent_message = self._phase_message.agent_messages[-1]

            # Increment the iteration count
            self.iteration_count += 1
            self.current_agent_index += 1

        if self._phase_message.summary == "incomplete":
            self._phase_message.set_summary("completed_failure")

        # Deallocate resources after completing iterations
        self.deallocate_resources()

        log_message(self._phase_message)
        return self._phase_message

    def _get_current_agent(self) -> Tuple[str, BaseAgent]:
        """Retrieve the next agent in a round-robin fashion."""
        agent = self.agents[self.current_agent_index % len(self.agents)]
        return agent

    def _get_last_agent(self) -> Tuple[str, BaseAgent]:
        """Retrieve the next agent in a round-robin fashion."""
        agent = self.agents[(self.current_agent_index - 1) % len(self.agents)]
        return agent
    
    async def set_interactive_mode(self, interactive: bool):
        self.phase_config.interactive = interactive
        print(f"Interactive mode for phase {self.name} set to {interactive}")
    
    @abstractmethod
    async def run_one_iteration(
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
    
    @property
    def last_agent_message(self) -> Optional[Message]:
        return self._last_agent_message