from abc import ABC, abstractmethod
import asyncio
import atexit
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type
from enum import Enum
import logging

from phase_messages.phase_message import PhaseMessage
from phases.base_phase import BasePhase
from resources.resource_manager import ResourceManager
from messages.message import Message
from utils.workflow_logger import workflow_logger
from agents.agent_manager import AgentManager

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class WorkflowStatus(Enum):
    """Status of workflow execution"""
    INCOMPLETE = "incomplete"
    COMPLETED_SUCCESS = "completed_success"
    COMPLETED_FAILURE = "completed_failure"

class PhaseStatus(Enum):
    """Status of phase execution"""
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

        self._initialize()
        self._setup_logger()
        self._setup_resource_manager()
        self._setup_agent_manager()
        self._create_phases()
        self._compute_resource_schedule()
        logger.info(f"Finished initializing workflow {self.name}")
        
        self.next_iteration_event = asyncio.Event()
        
        atexit.register(self._finalize_workflow)

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

    def _setup_logger(self):
        config = self._create_workflow_config()
        self.config = config
        self._initialize_workflow_logger(config)
        logger.info(f"Initialized workflow logger")

    def _create_workflow_config(self) -> WorkflowConfig:
        return WorkflowConfig(
            id=self.workflow_id,
            max_iterations=25,
            logs_dir=Path("logs"),
            task=self._get_task(),
            initial_prompt=self._get_initial_prompt(),
            metadata=self._get_metadata()
        )

    def _initialize_workflow_logger(self, config: WorkflowConfig):
        self.workflow_logger = workflow_logger
        self.workflow_logger.initialize(
            workflow_name=config.id,
            logs_dir=str(config.logs_dir),
            task=config.task
        )
        for key, value in config.metadata.items():
            self.workflow_logger.add_metadata(key, value)

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
    
    def run(self) -> None:
        """Execute the entire workflow by running all phases in sequence."""
        logger.info(f"Running workflow {self.name}")
        for _ in self._run_phases():
            continue

    async def _run_phases(self):
        try:
            if not self._root_phase:
                raise ValueError("No root phase registered")

            self._set_workflow_status(WorkflowStatus.INCOMPLETE)
            self._current_phase = self._root_phase
            prev_phase_message = self._get_initial_phase_message()

            while self._current_phase:
                logger.info(f"Running {self._current_phase.name}")
                self._set_phase_status(self._current_phase.name, PhaseStatus.INCOMPLETE)
                phase_message = await self._run_single_phase(self._current_phase, prev_phase_message)
                yield phase_message
                
                if phase_message.success:
                    self._set_phase_status(self._current_phase.name, PhaseStatus.COMPLETED_SUCCESS)
                else:
                    self._set_phase_status(self._current_phase.name, PhaseStatus.COMPLETED_FAILURE)

                if not phase_message.success or self._max_iterations_reached():
                    break
                    
                next_phases = self._phase_graph.get(self._current_phase, [])
                self._current_phase = next_phases[0] if next_phases else None
                prev_phase_message = phase_message

            if prev_phase_message.success:
                self._set_workflow_status(WorkflowStatus.COMPLETED_SUCCESS)
            else:
                self._set_workflow_status(WorkflowStatus.COMPLETED_FAILURE)

        except Exception as e:
            self._handle_workflow_exception(e)
    

    def _run_phases(self):
        try:
            if not self._root_phase:
                raise ValueError("No root phase registered")

            self._set_workflow_status(WorkflowStatus.INCOMPLETE)
            self._current_phase = self._root_phase
            prev_phase_message = self._get_initial_phase_message()

            while self._current_phase:
                logger.info(f"Running {self._current_phase.name}")
                self._set_phase_status(self._current_phase.name, PhaseStatus.INCOMPLETE)
                phase_message = self._run_single_phase(self._current_phase, prev_phase_message)
                yield phase_message
                
                if phase_message.success:
                    self._set_phase_status(self._current_phase.name, PhaseStatus.COMPLETED_SUCCESS)
                else:
                    self._set_phase_status(self._current_phase.name, PhaseStatus.COMPLETED_FAILURE)

                if not phase_message.success or self._max_iterations_reached():
                    break
                    
                next_phases = self._phase_graph.get(self._current_phase, [])
                self._current_phase = next_phases[0] if next_phases else None
                prev_phase_message = phase_message

            if prev_phase_message.success:
                self._set_workflow_status(WorkflowStatus.COMPLETED_SUCCESS)
            else:
                self._set_workflow_status(WorkflowStatus.COMPLETED_FAILURE)

        except Exception as e:
            self._handle_workflow_exception(e)

    def _set_workflow_status(self, status: WorkflowStatus):
        self.status = status

    def _set_phase_status(self, phase_name: str, status: PhaseStatus):
        self.workflow_logger.add_phase_status(phase_name, status.value)

    def _get_initial_phase_message(self) -> PhaseMessage:
        initial_message = Message(self.config.initial_prompt) if self.config.initial_prompt else None
        return PhaseMessage(agent_messages=[initial_message] if initial_message else [])

    async def _run_single_phase(self, phase: BasePhase, prev_phase_message: PhaseMessage) -> PhaseMessage:
        phase_instance = self._setup_phase(phase)
        phase_message = await phase_instance.run_phase(prev_phase_message)
        
        logger.status(f"Phase {phase.phase_config.phase_idx} completed: {phase.__class__.__name__} with success={phase_message.success}", phase_message.success)

        self._workflow_iteration_count += 1

        return phase_message

    def _run_single_phase(self, phase: BasePhase, prev_phase_message: PhaseMessage) -> PhaseMessage:
        phase_instance = self._setup_phase(phase)
        phase_message = phase_instance.run_phase(prev_phase_message)
        
        logger.status(f"Phase {phase.phase_config.phase_idx} completed: {phase.__class__.__name__} with success={phase_message.success}", phase_message.success)

        self._workflow_iteration_count += 1

        return phase_message
    
    async def edit_action_input_in_agent(self, action_id: str, new_input: str):
        _, agent_instance = self._current_phase._get_last_agent()
        print(f"In edit action going to run the last agent of {agent_instance.agent_id}")
        if hasattr(agent_instance, 'modify_memory_and_run'):
            result = await agent_instance.modify_memory_and_run(new_input)
            if result:
                print(f"Got result {result.message}")
                return result.message
        print("Doesn't have attribute")
        raise ValueError(f"No agent found that can modify action {action_id}")
    
    def edit_action_input_in_agent(self, action_id: str, new_input: str):
        _, agent_instance = self._current_phase._get_last_agent()
        print(f"In edit action going to run the last agent of {agent_instance.agent_id}")
        if hasattr(agent_instance, 'modify_memory_and_run'):
            result = agent_instance.modify_memory_and_run(new_input)
            if result:
                print(f"Got result {result.message}")
                return result.message
        print("Doesn't have attribute")
        raise ValueError(f"No agent found that can modify action {action_id}")
    
    async def set_message_input(self, user_input: str) -> str:
        result = await self._current_phase.set_message_input(user_input)
        
        # Trigger the next iteration
        self.next_iteration_event.set()
        
        return result
    
    def set_message_input(self, user_input: str) -> str:
        result = self._current_phase.set_message_input(user_input)
        
        # Trigger the next iteration
        self.next_iteration_event.set()
        
        return result
    
    async def get_last_message(self) -> str:
        result = self._current_phase.last_agent_message  
        return result.message if result else ""
    
    def get_last_message(self) -> str:
        result = self._current_phase.last_agent_message  
        return result.message if result else ""
    
    def _max_iterations_reached(self) -> bool:
        return self._workflow_iteration_count >= self.config.max_iterations

    def _finalize_workflow(self):
        self.workflow_logger.finalize(self.status.value)

    def _handle_workflow_exception(self, exception: Exception):
        self._set_workflow_status(WorkflowStatus.INCOMPLETE)
        self.workflow_logger.finalize(self.status.value)
        raise exception

    def _setup_phase(self, phase: BasePhase) -> BasePhase:
        try:
            logger.info(f"Setting up phase {phase.__class__.__name__}")
            phase.setup()
            return phase
        except Exception as e:
            self._set_workflow_status(WorkflowStatus.INCOMPLETE)
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