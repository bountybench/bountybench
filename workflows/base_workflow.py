from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type
from enum import Enum
import logging

from phase_responses.phase_response import PhaseResponse
from phases.base_phase import BasePhase
from responses.base_response import BaseResponse
from utils.workflow_logger import workflow_logger
from agents.agent_manager import AgentManager

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """Status of workflow execution"""
    INITIALIZED = "initialized"
    INCOMPLETE = "incomplete"
    COMPLETED_SUCCESS = "completed_success"
    COMPLETED_FAILURE = "completed_failure"
    COMPLETED_MAX_ITERATIONS = "completed_max_iterations"

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
    def __init__(self, **kwargs):
        self.workflow_id = self.name
        self.params = kwargs
        self.interactive = kwargs.get('interactive', False)
        self._current_phase_idx = 0
        self._workflow_iteration_count = 0
        self.phases: List[BasePhase] = []

        self._initialize()
        self._set_workflow_status(WorkflowStatus.INITIALIZED)
        self._setup_logger()
        self._setup_agent_manager()
        self._create_phases()
        self._compute_resource_schedule()

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

    def _get_task(self) -> Dict[str, Any]:
        return {}
    
    def _get_metadata(self) -> Dict[str, Any]:
        return {}
    
    def run(self) -> None:
        """Execute the entire workflow by running all phases in sequence."""
        for _ in self._run_phases():
            continue

    def _run_phases(self):
        """
        Execute all phases in sequence.
        Yields:
            PhaseResponse: The response from each phase.
        """
        try:
            self._set_workflow_status(WorkflowStatus.INCOMPLETE)
            prev_phase_response = self._get_initial_phase_response()

            for phase_idx, phase in enumerate(self.phases):
                phase_response = self._run_single_phase(phase_idx, prev_phase_response)
                
                if not phase_response.success or self._max_iterations_reached():
                    yield phase_response
                    break

                prev_phase_response = phase_response
                yield phase_response

            self._finalize_workflow()

        except Exception as e:
            self._handle_workflow_exception(e)

    def _set_workflow_status(self, status: WorkflowStatus):
        self.status = status

    def _get_initial_phase_response(self) -> PhaseResponse:
        initial_response = BaseResponse(self.config.initial_prompt) if self.config.initial_prompt else None
        return PhaseResponse(agent_responses=[initial_response] if initial_response else [])

    def _run_single_phase(self, phase_idx: int, prev_phase_response: PhaseResponse) -> PhaseResponse:
        self._current_phase_idx = phase_idx
        phase_instance = self._setup_phase(phase_idx)
        phase_response = phase_instance.run_phase(prev_phase_response)
        
        logger.info(f"Phase {phase_idx} completed: {phase_instance.__class__.__name__} with success={phase_response.success}")

        self._workflow_iteration_count += 1

        if not phase_response.success:
            self._set_workflow_status(WorkflowStatus.COMPLETED_FAILURE)
        elif self._max_iterations_reached():
            self._set_workflow_status(WorkflowStatus.COMPLETED_MAX_ITERATIONS)

        return phase_response

    def _max_iterations_reached(self) -> bool:
        return self._workflow_iteration_count >= self.config.max_iterations

    def _finalize_workflow(self):
        if self.status == WorkflowStatus.INCOMPLETE:
            self._set_workflow_status(WorkflowStatus.COMPLETED_SUCCESS)
        self.workflow_logger.finalize(self.status.value)

    def _handle_workflow_exception(self, exception: Exception):
        self._set_workflow_status(WorkflowStatus.INCOMPLETE)
        self.workflow_logger.finalize(self.status.value)
        raise exception

    def _setup_phase(self, phase_idx: int) -> BasePhase:
        """
        Setup and run a specific phase.
    
        Args:
            phase_idx (int): The index of the phase to set up.

        Returns:
            BasePhase: The phase instance.
        """
        try:
            phase_instance = self.phases[phase_idx]

            logger.info(f"Setting up phase {phase_idx}: {phase_instance.__class__.__name__}")

            # Setup the phase
            phase_instance.setup()

            return phase_instance

        except Exception as e:
            self.status = WorkflowStatus.INCOMPLETE
            logger.error(f"Failed to set up phase {phase_idx}: {e}")
            raise

        except Exception as e:
            self._set_workflow_status(WorkflowStatus.INCOMPLETE)
            logger.error(f"Failed to set up phase {phase_idx}: {e}")
            raise

    def _compute_resource_schedule(self):
        """
        Compute the agent (which will compute resource) schedule across all phases.
        """
        phase_classes = [type(phase) for phase in self.phases]
        self.agent_manager.compute_resource_schedule(phase_classes)
        logger.debug("Computed resource schedule for all phases based on agents.")

    def register_phase(self, phase: BasePhase):
        phase_idx = len(self.phases)
        phase.phase_config.phase_idx = phase_idx
        self.phases.append(phase)
        logger.debug(f"Registered phase {phase_idx}: {phase.__class__.__name__}")
        logger.info(f"{phase.name} registered with config: {phase.phase_config}")

    @property
    def name(self):
        return self.__class__.__name__