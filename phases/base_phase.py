import time
from abc import ABC, abstractmethod
from asyncio import QueueEmpty
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent, IterationFailure
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.message_utils import log_message
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from resources.base_resource import BaseResourceConfig
from resources.resource_type import ResourceType
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


if TYPE_CHECKING:
    from workflows.base_workflow import BaseWorkflow


@dataclass
class PhaseConfig:
    phase_name: str
    agent_configs: List[Tuple[str, "AgentConfig"]] = field(default_factory=list)
    max_iterations: int = field(default=10)
    interactive: bool = False
    phase_idx: Optional[int] = None

    @classmethod
    def from_phase(cls, phase_instance: "BasePhase", **kwargs):
        # Filter out kwargs that are not attributes of PhaseConfig
        valid_kwargs = {k: v for k, v in kwargs.items() if k in cls.__annotations__}

        config = cls(
            phase_name=phase_instance.name,
            agent_configs=phase_instance.define_agents(),
            **valid_kwargs,
        )
        return config


class BasePhase(ABC):
    AGENT_CLASSES: List[Type[BaseAgent]] = []

    def __init__(self, workflow: "BaseWorkflow", **kwargs):
        self.workflow: "BaseWorkflow" = workflow
        self.workflow_id = workflow.workflow_message.workflow_id
        self.phase_config: PhaseConfig = PhaseConfig.from_phase(self, **kwargs)

        self.agent_manager: Any = self.workflow.agent_manager
        self.resource_manager: Any = self.workflow.resource_manager
        self.agents: List[Tuple[str, BaseAgent]] = []
        self.params: Dict[str, Any] = kwargs
        self._done: bool = False
        self.iteration_count: int = 0
        self._last_agent_message: Optional[Message] = None
        logger.debug(f"Created {self.name} phase with config: {self.phase_config}")

    @abstractmethod
    def define_resources(
        self,
    ) -> List[Tuple[ResourceType, Optional[BaseResourceConfig]]]:
        """
        Define the resources required for this phase.

        Returns:
            List[Tuple[Type[DefaultResource], Optional[BaseResourceConfig]]]:
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

    def get_phase_resources(self) -> Dict[str, Any]:
        """
        Get the resources required for all agents in this phase.

        Returns:
            Dict[str, Any]: A dictionary of resources required by all agents.
        """
        phase_resources = {}
        for agent_class in self.AGENT_CLASSES:
            phase_resources.update(agent_class.REQUIRED_RESOURCES)
        return phase_resources

    def __rshift__(self, other: "BasePhase") -> "BasePhase":
        """
        Define the order of phases in the workflow.

        This method is used to create a directed graph of phases. It's typically
        used in the workflow setup, like:
        exploit_phase = ExploitPhase(workflow=self, **phase_kwargs)
        patch_phase = PatchPhase(workflow=self, **phase_kwargs)
        exploit_phase >> patch_phase

        Args:
            other (BasePhase): The next phase in the workflow.

        Returns:
            BasePhase: The 'other' phase, allowing for method chaining.
        """
        if isinstance(other, BasePhase):
            if self not in self.workflow._phase_graph:
                self.workflow.register_phase(self)
            if other not in self.workflow._phase_graph:
                self.workflow.register_phase(other)
            self.workflow._phase_graph[self].append(other)
        return other

    @classmethod
    def get_required_resources(cls) -> Set[ResourceType]:
        """
        Get the set of required resources for all agents in this phase.

        Returns:
            Set[str]: A set of resource names required by all agents.
        """
        resources = set()
        for agent_cls in cls.AGENT_CLASSES:
            resources.update(agent_cls.REQUIRED_RESOURCES)
        return resources

    def setup(self) -> None:
        """
        Initialize and register resources and agents for the phase.
        """
        logger.debug(f"Entering setup for {self.name}")

        # 1. Define and register resources
        resource_configs = self.define_resources()
        resource_configs_keys = {
            resource.key(self.workflow_id) for resource, _ in resource_configs
        }
        for resource, resource_config in resource_configs:
            resource_id, resource_class = (
                resource.key(self.workflow_id),
                resource.get_class(),
            )
            if not self.resource_manager.is_resource_equivalent(
                resource_id, resource_class, resource_config
            ):
                self.resource_manager.register_resource(
                    resource_id, resource_class, resource_config
                )

        # 2. Initialize phase resources
        self.resource_manager.initialize_phase_resources(
            self.phase_config.phase_idx, resource_configs_keys
        )
        logger.debug(f"Resources for phase {self.name} initialized")
        # 3. Define and register agents
        agent_configs = self.define_agents()

        try:
            # 1. Define and register resources
            resource_configs = self.define_resources()
            for resource, resource_config in resource_configs:
                resource_id, resource_class = (
                    resource.key(self.workflow_id),
                    resource.get_class(),
                )
                if not self.resource_manager.is_resource_equivalent(
                    resource_id, resource_class, resource_config
                ):
                    self.resource_manager.register_resource(
                        resource_id, resource_class, resource_config
                    )

            logger.debug(f"Completed resource setup for {self.name}")

            # 3. Define and register agents
            agent_configs = self.define_agents()
            self.agent_manager.initialize_phase_agents(agent_configs)
            logger.debug(f"Agents for phase {self.name} initialized")
            self.agents = list(self.agent_manager._phase_agents.items())

            logger.debug(f"Completed agent setup for {self.name}")
        except Exception as e:
            logger.error(f"Error during setup for phase {self.name}: {e}")
            raise

    def deallocate_resources(self) -> None:
        """
        Deallocate resources after the phase is completed.
        """
        try:
            self.resource_manager.deallocate_phase_resources(
                self.phase_config.phase_idx
            )
            logger.debug(
                f"Phase {self.phase_config.phase_idx} ({self.phase_config.phase_name}) resources deallocated."
            )
        except Exception as e:
            logger.error(
                f"Failed to deallocate resources for phase {self.phase_config.phase_idx}: {e}"
            )
            raise

    async def run(self, prev_phase_message: PhaseMessage) -> PhaseMessage:
        """
        Execute the phase by running its iterations.

        Args:
            prev_phase_message (PhaseMessage): The message from the previous phase.

        Returns:
            PhaseMessage: The message of the current phase.
        """

        logger.info(
            f"running Phase {self.name} starting at iteration {self.iteration_count}"
        )

        if self.iteration_count == 0 and (
            not hasattr(self, "_phase_message") or not self._phase_message
        ):
            self._phase_message = PhaseMessage(
                phase_id=self.name,
                max_iterations=self.phase_config.max_iterations,
                phase_idx=self.phase_config.phase_idx,
                prev=prev_phase_message,
            )

            self._initialize_last_agent_message(prev_phase_message)

        start_count = self.iteration_count
        # Start the iteration at the current count
        for iteration_num in range(start_count, self.phase_config.max_iterations):

            if self._phase_message.complete:
                break

            await self._handle_interactive_mode()

            await self._run_iteration()

            if self._phase_message.complete:
                self._phase_message.set_submit()
                break

            self.iteration_count += 1
        if not self._phase_message.complete:
            await self._run_iteration(check=True)
            summary = "no_submission"
            if self._last_agent_message.success:
                self._phase_message.set_success()
                summary += "/success"
            else:
                summary += "/failure"
            self._phase_message.set_summary(summary)
        self._finalize_phase()

        log_message(self._phase_message)
        return self._phase_message

    def _initialize_last_agent_message(self, prev_phase_message: PhaseMessage) -> None:
        """Initialize the last agent message based on the previous phase message."""
        if prev_phase_message and len(prev_phase_message.agent_messages) > 0:
            self._last_agent_message = prev_phase_message.agent_messages[-1]
        else:
            logger.debug(f"Adding initial prompt to phase")
            self._create_initial_agent_message()

    def _create_initial_agent_message(self) -> None:
        """Create the initial agent message for the phase."""
        self._last_agent_message = AgentMessage(
            agent_id="system",
            message=self.params.get("initial_prompt").format(**self.params),
        )
        self._last_agent_message.set_iteration(-1)
        self._phase_message.add_child_message(self._last_agent_message)

    async def _handle_interactive_mode(self) -> None:
        """Handle the interactive mode if enabled."""
        if self.phase_config.interactive:
            if hasattr(self.workflow, "next_iteration_queue"):
                logger.info("Waiting for 'next' signal ...")
                await self.workflow.next_iteration_queue.get()
            else:
                logger.warning(
                    "Interactive mode is set, but workflow doesn't have next_iteration_queue"
                )

    async def _run_iteration(self, check: bool = False) -> None:
        """Run a single iteration based on last message."""
        iteration = self.get_current_iteration()
        agent_id, agent_instance = self._get_current_agent(get_prev=check)
        logger.info(f"Running iteration {iteration} of {self.name} with {agent_id}")

        start_time = time.time()

        agent_message = None
        try:
            agent_message: AgentMessage = await self.run_one_iteration(
                phase_message=self._phase_message,
                agent_instance=agent_instance,
                previous_output=self._last_agent_message,
            )
            agent_message.set_complete()
            logger.info(
                f"Finished iteration {iteration} of {self.name} with {agent_id}"
            )
        except IterationFailure as e:
            agent_message = e.agent_message
            logger.error(f"Iteration {iteration} failed: {str(e)}")
            raise e
        except Exception as e:
            logger.exception("Unexpected error during iteration")
            raise e
        finally:
            if agent_message:
                iteration_time = time.time() - start_time
                iteration_time_ms = iteration_time * 1000
                agent_message.set_iteration(iteration)
                agent_message.set_iteration_time_ms(iteration_time_ms)

                await self.set_last_agent_message(agent_message)
                self._phase_message.add_child_message(agent_message)

    async def _pause_phase(self) -> None:
        """Pause the phase if an iteration fails."""
        await self.set_interactive_mode(True)
        # Clear any outstanding next_iteration calls
        if hasattr(self.workflow, "next_iteration_queue"):
            logger.debug("Clearing next iteration queue")
            while not self.workflow.next_iteration_queue.empty():
                await self.workflow.next_iteration_queue.get()

        logger.info(f"Phase {self.name} paused due to error.")

    def _finalize_phase(self) -> None:
        """Finalize the phase by setting the summary and deallocating resources."""
        if self._phase_message.summary == "incomplete":
            self._phase_message.set_summary("completed_failure")
        self.deallocate_resources()
        # Drain any pending 'next' signals without awaiting
        while True:
            try:
                self.workflow.next_iteration_queue.get_nowait()
            except QueueEmpty:
                break

    def get_current_iteration(self) -> int:
        """
        Get the current iteration number for the next agent message.
        First agent message in phase is always iteration 1, regardless of previous phase.

        Returns:
            int: The current iteration (depth)
        """
        if (
            not self.last_agent_message
            or self.last_agent_message.parent != self._phase_message
            or self.last_agent_message.iteration == None
        ):
            return 0
        else:
            return self.last_agent_message.iteration + 1

    def _get_agent_from_message(self, message: AgentMessage) -> Optional[BaseAgent]:
        """
        Retrieve the agent associated with iteration from a given message.

        Returns:
            Tuple[str, BaseAgent]: A tuple containing the agent ID and the agent instance.
        """
        iteration = message.iteration
        if iteration == None or iteration == -1:
            logger.warning(f"Message {message} iteration unset or negative")
            return None
        agent = self.agents[iteration % len(self.agents)]
        return agent

    def _get_current_agent(self, get_prev: bool = False) -> Tuple[str, BaseAgent]:
        """
        Retrieve the agent in a round-robin fashion.

        Args:
            get_prev (bool): Whether to get the previous agent instead of the next one.

        Returns:
            Tuple[str, BaseAgent]: A tuple containing the agent ID and the agent instance.
        """
        iteration = self.get_current_iteration()
        if get_prev:
            iteration -= 1
            iteration = max(0, iteration)
        agent = self.agents[iteration % len(self.agents)]
        return agent

    async def set_interactive_mode(self, interactive: bool) -> None:
        """
        Set the interactive mode for the phase.

        Args:
            interactive (bool): Whether to enable interactive mode.
        """
        self.phase_config.interactive = interactive
        logger.info(f"Interactive mode for phase {self.name} set to {interactive}")

    @abstractmethod
    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message],
    ) -> Message:
        """
        Run a single iteration of the phase.

        Args:
            phase_message (PhaseMessage): The current phase message.
            agent_instance (BaseAgent): The agent to run.
            previous_output (Optional[Message]): The output from the previous iteration.

        Returns:
            Message: The message from the agent.
        """
        pass

    @property
    def name(self) -> str:
        """
        Get the name of the phase.

        Returns:
            str: The name of the phase (class name).
        """
        return self.__class__.__name__

    @property
    def last_agent_message(self) -> Optional[Message]:
        """
        Get the last agent message.

        Returns:
            Optional[Message]: The last agent message, if any.
        """
        return self._last_agent_message

    async def set_last_agent_message(self, message: AgentMessage) -> Optional[Message]:
        """
        Set the last agent message to run from for phase.
        """
        self._last_agent_message = message
