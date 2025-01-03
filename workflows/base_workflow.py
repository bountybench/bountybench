from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from agents.agent_manager import AgentManager

from enum import Enum
import logging

# Import your specific modules and classes here
from phases.base_phase import BasePhase, PhaseConfig
from responses.base_response import BaseResponse
from utils.workflow_logger import workflow_logger

# Initialize the module-level logger
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
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseWorkflow(ABC):
    def __init__(self, **kwargs):
        self.params = kwargs
        self._initialize()
        
        self.status = WorkflowStatus.INITIALIZED
        self._current_phase_idx = 0
        self._workflow_iteration_count = 0

        # Initialize ResourceManager
        self.agent_manager = AgentManager()

        # List to store phase instances
        self.phases: List[BasePhase] = []       

        self._create_phases()
        self._compute_resource_schedule()

    @abstractmethod
    def _create_phases(self):
        """Create and register phases. To be implemented by subclasses."""
        pass

    @abstractmethod
    def _get_initial_prompt(self) -> str:
        """Provide the initial prompt for the workflow."""
        pass

    def _initialize(self):
        """Handles any task level setup pre-resource/agent/phase creation. Also handles logger initialization"""
        self.workflow_id = self.params['workflow_id']
        
        # Setup workflow config
        config = WorkflowConfig(
            id=self.workflow_id,
            max_iterations=25,
            logs_dir=Path("logs"),
            initial_prompt=self._get_initial_prompt(),
            metadata={
            }
        )

        self.config = config

        self.workflow_logger = workflow_logger
        self.workflow_logger.initialize(
            workflow_name=config.id,
            logs_dir=str(config.logs_dir),
        )

        # Add workflow metadata
        for key, value in config.metadata.items():
            self.workflow_logger.add_metadata(key, value)

    def run(self) -> None:
        """
        Execute the entire workflow by running all phases in sequence.
        This is a convenience method that runs the workflow to completion.
        """
        # Run through all phases
        for _ in self._run_phases():
            continue

    def _run_phases(self):
        """
        Execute all phases in sequence.
        Yields:
            Tuple[BaseResponse, bool]: The response from each phase and a success flag.
        """
        try:
            self.status = WorkflowStatus.INCOMPLETE
            prev_response = BaseResponse(self.config.initial_prompt) if self.config.initial_prompt else None

            for phase_idx, phase in enumerate(self.phases):
                self._current_phase_idx = phase_idx

                # Setup and run the phase
                phase_instance = self._setup_phase(phase_idx, prev_response)
                phase_response, phase_success = phase_instance.run_phase()
                
                logger.info(f"Phase {phase_idx} completed: {phase_instance.__class__.__name__} with success={phase_success}")

                # Update workflow state
                prev_response = phase_response
                if not phase_success:
                    self.status = WorkflowStatus.COMPLETED_FAILURE
                    yield phase_response, phase_success
                    break

                self._workflow_iteration_count += 1
                if self._workflow_iteration_count >= self.config.max_iterations:
                    self.status = WorkflowStatus.COMPLETED_MAX_ITERATIONS
                    yield phase_response, phase_success
                    break

                # Yield current phase results
                yield phase_response, phase_success

            else:
                # If all phases completed successfully
                self.status = WorkflowStatus.COMPLETED_SUCCESS

            # Finalize workflow
            self.workflow_logger.finalize(self.status.value)

        except Exception as e:
            self.status = WorkflowStatus.INCOMPLETE
            self.workflow_logger.finalize(self.status.value)
            raise e

    def _setup_phase(self, phase_idx: int, initial_response: Optional[BaseResponse] = None) -> BasePhase:
        """
        Setup and run a specific phase.
    
        Args:
            phase_idx (int): The index of the phase to set up.
            initial_response (Optional[BaseResponse]): The initial response for the phase.

        Returns:
            BasePhase: The phase instance.
        """
        try:
            phase_instance = self.phases[phase_idx]
            logger.info(f"Setting up phase {phase_idx}: {phase_instance.name}")

            if initial_response:
                phase_instance.initial_response = initial_response
                logger.info(f"Set initial response for phase {phase_idx}")
            else:
                logger.info(f"No initial response provided for phase {phase_idx}")

            # Setup the phase
            phase_instance.setup()
            return phase_instance

        except Exception as e:
            self.status = WorkflowStatus.INCOMPLETE
            logger.error(f"Failed to set up phase {phase_idx}: {e}")
            raise

    def _compute_resource_schedule(self):
        """
        Compute the agent (which will compute resource) schedule across all phases.
        """
        phase_classes = [type(phase) for phase in self.phases]
        self.agent_manager.compute_resource_schedule(phase_classes)
        logger.debug("Computed resource schedule for all phases based on agents.")

    @property
    def current_phase(self) -> Optional[PhaseConfig]:
        """Get current phase configuration"""
        if 0 <= self._current_phase_idx < len(self.phases):
            return self.phases[self._current_phase_idx].phase_config
        return None

    def register_phase(self, phase: BasePhase):
        phase_idx = len(self.phases)
        phase.phase_config.phase_idx = phase_idx  # Set phase index
        self.phases.append(phase)
        logger.debug(f"Registered phase {phase_idx}: {phase.__class__.__name__}")
        logger.info(f"{phase.name} registered with config: {phase.phase_config}")