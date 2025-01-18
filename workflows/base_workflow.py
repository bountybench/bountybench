from abc import ABC, abstractmethod
import asyncio
import atexit
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Type
from enum import Enum
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from phases.base_phase import BasePhase
from resources.resource_manager import ResourceManager
from agents.agent_manager import AgentManager

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class WorkflowStatus(Enum):
    """Status of workflow execution"""
    INCOMPLETE = "incomplete"
    COMPLETED_SUCCESS = "completed_success"
    COMPLETED_FAILURE = "completed_failure"

@dataclass
class WorkflowConfig:
    """Configuration for a workflow"""
    id: str
    max_iterations: int
    logs_dir: Path
    initial_prompt: str
    task: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseWorkflow(ABC):
    status = WorkflowStatus.INCOMPLETE
    
    def __init__(self, **kwargs):
        logger.info(f"Initializing workflow {self.name}")
        self.workflow_id = self.name
        self.params = kwargs
        self.interactive = kwargs.get('interactive', False)
        if kwargs.get("phase_iterations"):
            self.phase_iterations = kwargs.get("phase_iterations")
        self._current_phase_idx = 0
        self._workflow_iteration_count = 0
        self._phase_graph = {}  # Stores phase relationships
        self._root_phase = None
        self._current_phase = None


        workflow_message.workflow_name = self.name
        workflow_message.task = self._get_task()
        self.workflow_message = workflow_message

        self._initialize()
        self._setup_resource_manager()
        self._setup_agent_manager()
        self._create_phases()
        self._compute_resource_schedule()
        logger.info(f"Finished initializing workflow {self.name}")
        
        self.next_iteration_event = asyncio.Event()
        
        atexit.register()

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

        phase_instance = phase_class(workflow=self, interactive=self.interactive, **kwargs)
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
        self.agent_manager = AgentManager()
        logger.info("Setup agent manager")

    def _setup_resource_manager(self):
        self.resource_manager = ResourceManager()
        logger.info("Setup resource manager")

    def _get_task(self) -> Dict[str, Any]:
        return {}
    
    def _get_metadata(self) -> Dict[str, Any]:
        return {}
    
    async def run(self) -> None:
        """Execute the entire workflow by running all phases in sequence."""
        logger.info(f"Running workflow {self.name}")
        async for _ in self._run_phases():
            continue

    async def _run_phases(self):
        prev_phase_message = None
        prev_phase_message = None
        try:
            if not self._root_phase:
                raise ValueError("No root phase registered")

            self.workflow_message.set_complete(False)
            self.workflow_message.set_complete(False)
            self._current_phase = self._root_phase

            while self._current_phase:
                logger.info(f"Running {self._current_phase.name}")
                phase_message = await self._run_single_phase(self._current_phase, prev_phase_message)
                yield phase_message

                self.workflow_message.add_phase_message(phase_message)


                self.workflow_message.add_phase_message(phase_message)


                if not phase_message.success or self._max_iterations_reached():
                    break
                    
                next_phases = self._phase_graph.get(self._current_phase, [])
                self._current_phase = next_phases[0] if next_phases else None
                prev_phase_message = phase_message

            if prev_phase_message.success:
                self.workflow_message.set_success(WorkflowStatus.COMPLETED_SUCCESS)
                self.workflow_message.set_success(WorkflowStatus.COMPLETED_SUCCESS)
            else:
                self.workflow_message.set_success(WorkflowStatus.COMPLETED_FAILURE)
                self.workflow_message.set_success(WorkflowStatus.COMPLETED_FAILURE)

        except Exception as e:
            self._handle_workflow_exception(e)

    async def _run_single_phase(self, phase: BasePhase, prev_phase_message: PhaseMessage) -> PhaseMessage:
        phase_instance = self._setup_phase(phase)

        for agent_name, agent in phase_instance.agents:
            self.workflow_message.add_agent(agent_name, agent)

        for resource_id, resource in phase_instance.resource_manager._resources.id_to_resource.items():
            self.workflow_message.add_resource(resource_id, resource)

        for agent_name, agent in phase_instance.agents:
            self.workflow_message.add_agent(agent_name, agent)

        for resource_id, resource in phase_instance.resource_manager._resources.id_to_resource.items():
            self.workflow_message.add_resource(resource_id, resource)
        phase_message = await phase_instance.run_phase(prev_phase_message)
        
        logger.status(f"Phase {phase.phase_config.phase_idx} completed: {phase.__class__.__name__} with success={phase_message.success}", phase_message.success)

        self._workflow_iteration_count += 1

        return phase_message

    async def set_message_input(self, user_input: str) -> str:
        result = await self._current_phase.set_message_input(user_input)
        
        # Trigger the next iteration
        self.next_iteration_event.set()
        
        return result
    
    async def get_last_message(self) -> str:
        result = self._current_phase.last_agent_message  
        return result.message if result else ""
    
    def _max_iterations_reached(self) -> bool:
        return self._workflow_iteration_count >= self.config.max_iterations

    def _handle_workflow_exception(self, exception: Exception):
        self.workflow_message.set_complete(WorkflowStatus.INCOMPLETE)
        self.workflow_message.set_complete(WorkflowStatus.INCOMPLETE)
        raise exception

    def _setup_phase(self, phase: BasePhase) -> BasePhase:
        try:
            logger.info(f"Setting up phase {phase.__class__.__name__}")
            phase.setup()
            return phase
        except Exception as e:
            self.workflow_message.set_complete(WorkflowStatus.INCOMPLETE)
            self.workflow_message.set_complete(WorkflowStatus.INCOMPLETE)
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
            logger.debug(f"Registered phase { phase.phase_config.phase_idx}: {phase.__class__.__name__}")
            logger.info(f"{phase.phase_config.phase_name} registered")

    @property
    def name(self):
        return self.__class__.__name__
    
    @property
    def initial_prompt(self):
        return self.config.initial_prompt