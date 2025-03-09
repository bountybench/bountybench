import asyncio
import atexit
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Type

from agents.agent_manager import AgentManager
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from phases.base_phase import BasePhase
from resources.resource_manager import ResourceManager
from utils.logger import get_main_logger
from workflows.interactive_controller import InteractiveController

logger = get_main_logger(__name__)


class BaseWorkflow(ABC):

    def __init__(self, **kwargs):
        logger.info(f"Initializing workflow {self.name}")
        self.params = kwargs
        self.interactive = kwargs.get("interactive", False)
        if kwargs.get("phase_iterations"):
            self.phase_iterations = kwargs.get("phase_iterations")

        self.max_iterations = 25
        self._current_phase_idx = 0
        self._workflow_iteration_count = 0
        self._phase_graph = {}  # Stores phase relationships
        self._root_phase = None
        self._current_phase = None

        self._initialize()

        self.initial_prompt = self._get_initial_prompt()

        self.workflow_message = WorkflowMessage(
            workflow_name=self.name,
            task=self.task,
            additional_metadata=self._get_metadata(),
        )

        self.workflow_id = self.workflow_message.workflow_id

        self._check_docker_desktop_availability()
        self._setup_resource_manager()
        self._setup_agent_manager()
        self._setup_interactive_controller()
        self._create_phases()
        self._compute_resource_schedule()
        logger.info(f"Finished initializing workflow {self.name}")

        self.next_iteration_event = asyncio.Event()

        atexit.register(self._finalize_workflow)

    def _finalize_workflow(self):
        self.workflow_message.save()

    def _register_root_phase(self, phase: BasePhase):
        """Register the starting phase of the workflow."""
        self._root_phase = phase
        self.register_phase(phase)
        logger.info(f"Registered root phase {phase.name}")

    def register_phase(self, phase: BasePhase):
        """Register a phase and its dependencies."""
        if phase not in self._phase_graph:
            self._phase_graph[phase] = []
            logger.debug(f"Registered phase: {phase.__class__.__name__}")

    @abstractmethod
    def _create_phases(self):
        """Create and register phases. To be implemented by subclasses."""
        pass

    @property
    def task(self):
        return self._get_task()

    @property
    def current_phase(self):
        return self._current_phase

    @property
    def phase_graph(self):
        return self._phase_graph

    def _create_phase(self, phase_class: Type[BasePhase], **kwargs: Any) -> None:
        """
        Create a phase instance and register it with the workflow.

        Args:
            phase_class (Type[BasePhase]): The class of the phase to create.
            **kwargs: Additional keyword arguments to pass to the phase constructor.

        Raises:
            TypeError: If the provided class is not a subclass of BasePhase.
        """
        if not issubclass(phase_class, BasePhase):
            raise TypeError(f"{phase_class.__name__} is not a subclass of BasePhase")

        phase_instance = phase_class(
            workflow=self, interactive=self.interactive, **kwargs
        )
        self.register_phase(phase_instance)
        logger.info(f"Created and registered phase: {phase_class.__name__}")

    @abstractmethod
    def _get_initial_prompt(self) -> str:
        """Provide the initial prompt for the workflow."""
        pass

    def _initialize(self):
        """Handles any task level setup pre-resource/agent/phase creation and sets additional params."""
        pass

    def _setup_agent_manager(self):
        self.agent_manager = AgentManager(workflow_id=self.workflow_id)
        logger.info("Setup agent manager")

    def _setup_resource_manager(self):
        self.resource_manager = ResourceManager(workflow_id=self.workflow_id)
        logger.info("Setup resource manager")

    def _setup_interactive_controller(self):
        self.interactive_controller = InteractiveController(self)
        logger.info("Setup interactive controller")

    def _get_task(self) -> Dict[str, Any]:
        return {}

    def _get_metadata(self) -> Dict[str, Any]:
        return {}

    def _check_docker_desktop_availability(self):
        # Check Docker Desktop availability
        try:
            subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "Docker Desktop is not running. Please start Docker Desktop before starting the workflow"
            )

    async def run(self) -> None:
        """Execute the entire workflow by running all phases in sequence."""
        logger.info(f"Running workflow {self.name}")
        async for _ in self._run_phases():
            continue

    async def _run_phases(self):
        prev_phase_message = None
        try:
            if not self._root_phase:
                raise ValueError("No root phase registered")

            self._current_phase = self._root_phase

            while self._current_phase:
                logger.info(f"Running {self._current_phase.name}")
                phase_message = await self._run_single_phase(
                    self._current_phase, prev_phase_message
                )
                yield phase_message

                prev_phase_message = phase_message
                if not phase_message.success or self._max_iterations_reached():
                    break

                next_phases = self._phase_graph.get(self._current_phase, [])
                self._current_phase = next_phases[0] if next_phases else None

            if prev_phase_message.success:
                self.workflow_message.set_success()

            self.workflow_message.set_complete()
            self.workflow_message.save()

        except Exception as e:
            self._handle_workflow_exception(e)

    async def _run_single_phase(
        self, phase: BasePhase, prev_phase_message: PhaseMessage
    ) -> PhaseMessage:
        phase_instance = self._setup_phase(phase)
        for agent_name, agent in phase_instance.agents:
            self.workflow_message.add_agent(agent_name, agent)

        for (
            resource_id,
            resource,
        ) in phase_instance.resource_manager._resources.id_to_resource.get(
            self.workflow_id, {}
        ).items():
            self.workflow_message.add_resource(resource_id, resource)

        phase_message = await phase_instance.run(
            self.workflow_message, prev_phase_message
        )

        logger.status(
            f"Phase {phase.phase_config.phase_idx} completed: {phase.__class__.__name__} with success={phase_message.success}",
            phase_message.success,
        )

        self._workflow_iteration_count += 1

        return phase_message

    def _max_iterations_reached(self) -> bool:
        return self._workflow_iteration_count >= self.max_iterations

    def _handle_workflow_exception(self, exception: Exception):
        raise exception

    def _setup_phase(self, phase: BasePhase) -> BasePhase:
        try:
            logger.info(f"Setting up phase {phase.__class__.__name__}")
            phase.setup()
            return phase
        except Exception as e:
            logger.error(f"Failed to set up phase: {e}")
            raise

    def _compute_resource_schedule(self):
        """
        Compute the agent (which will compute resource) schedule across all phases.
        """
        phases = self._phase_graph.keys()
        self.resource_manager.compute_schedule(phases)
        logger.debug("Computed resource schedule for all phases based on agents.")

    def register_phase(self, phase: BasePhase):
        if phase not in self._phase_graph:
            self._phase_graph[phase] = []
            phase.phase_config.phase_idx = len(self._phase_graph) - 1
            logger.debug(
                f"Registered phase { phase.phase_config.phase_idx}: {phase.__class__.__name__}"
            )
            logger.info(f"{phase.phase_config.phase_name} registered")

    async def stop(self):
        # Deallocate agents and resources
        self.agent_manager.deallocate_all_agents()
        self.resource_manager.deallocate_all_resources()

        if hasattr(self, "next_iteration_event"):
            self.next_iteration_event.clear()

        self._finalize_workflow()

    async def restart(self):
        self._initialize()

        self._setup_resource_manager()
        self._setup_agent_manager()
        self._setup_interactive_controller()
        self._compute_resource_schedule()

        self.next_iteration_event = asyncio.Event()
        self.workflow_message.new_log()
        logger.info(f"Restarted workflow {self.name}")

    async def run_restart(self):
        logger.info(f"Running restarted workflow {self.name}")
        # pick up running from current phase
        self._current_phase.setup()
        agent_configs = self._current_phase.define_agents()
        self.agent_manager.initialize_phase_agents(agent_configs)

        phase_message = await self._current_phase.run(self.workflow_message, None)

        logger.status(
            f"Phase {self._current_phase.phase_config.phase_idx} completed: {self._current_phase.__class__.__name__} with success={phase_message.success}",
            phase_message.success,
        )

        self._workflow_iteration_count += 1
        next_phases = self._phase_graph.get(self._current_phase, [])
        self._current_phase = next_phases[0] if next_phases else None

        # Continue running the remaining phases (if any)
        if self._current_phase:
            try:
                async for _ in self._run_phases():
                    continue
            except asyncio.CancelledError:
                logger.info("workflow phases run was cancelled")
                raise

    @property
    def name(self):
        return self.__class__.__name__
