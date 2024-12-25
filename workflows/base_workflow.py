from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from phases.base_phase import BasePhase, PhaseConfig
from utils.workflow_logger import workflow_logger
from responses.response import Response

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
    name: str
    max_iterations: int
    logs_dir: Path
    task_repo_dir: Path
    bounty_number: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    phase_configs: List[PhaseConfig] = field(default_factory=list)

class BaseWorkflow(ABC):
    """
    Base class for defining workflows that coordinate phases and their agents.
    
    A workflow:
    - Acts as top-level controller for phases
    - Manages workflow-level logging
    - Coordinates phase transitions and data flow between phases
    - Tracks overall workflow state and completion status
    """

    def __init__(self, config: WorkflowConfig):
        """Initialize workflow with configuration"""
        self.config = config
        self.status = WorkflowStatus.INITIALIZED
        self._current_phase_idx = 0
        self._iteration_count = 0
        
        # Initialize workflow logger
        self.workflow_logger = workflow_logger
        self.workflow_logger.initialize(
            workflow_name=config.name,
            logs_dir=str(config.logs_dir),
            task_repo_dir=str(config.task_repo_dir),
            bounty_number=str(config.bounty_number)
        )
        
        # Add workflow metadata
        for key, value in config.metadata.items():
            self.workflow_logger.add_metadata(key, value)
    
    @abstractmethod
    def setup_init(self) -> None:
        """Setup workflow initialization"""
        pass

    @abstractmethod
    def setup_resources(self) -> None:
        """Setup all required resources"""
        pass

    @abstractmethod
    def setup_agents(self) -> None:
        """Setup and configure agents"""
        pass

    def setup_phases(self) -> None:
        """
        Setup workflow phases and resources.
        This orchestrates the setup process in the correct order with logging.
        """
        try:
            # Initial setup
            self.setup_init()

            # Resource setup
            self.setup_resources()

            # Agent setup
            self.setup_agents()

        except Exception as e:
            self.status = WorkflowStatus.INCOMPLETE
            raise e

    def _validate_phase_configs(self) -> None:
        """Validate phase configurations before execution"""
        if not self.config.phase_configs:
            raise ValueError("No phase configurations provided")
            
        # Validate phase numbers are sequential starting from 1
        phase_numbers = [p.phase_number for p in self.config.phase_configs]
        if sorted(phase_numbers) != list(range(1, len(phase_numbers) + 1)):
            raise ValueError("Phase numbers must be sequential starting from 1")

    @abstractmethod
    def create_phase(self, phase_config: PhaseConfig, prev_response: Optional[Response]) -> BasePhase:
        """
        Create a phase instance from config.
        Must be implemented by subclasses to return appropriate phase types.
        """
        pass

    def run(self) -> None:
        """
        Execute the workflow by running phases in sequence.
        """
        try:
            self._validate_phase_configs()
            self.setup_phases()
            self.status = WorkflowStatus.INCOMPLETE
            
            prev_response = None
            
            # Execute phases in sequence
            for phase_idx, phase_config in enumerate(self.config.phase_configs):
                self._current_phase_idx = phase_idx
                
                # Create and run phase
                phase = self.create_phase(phase_config, prev_response)
                phase_response, phase_success = phase.run_phase()
                
                # Update workflow state
                prev_response = phase_response
                if not phase_success:
                    self.status = WorkflowStatus.COMPLETED_FAILURE
                    break
                    
                self._iteration_count += 1
                if self._iteration_count >= self.config.max_iterations:
                    self.status = WorkflowStatus.COMPLETED_MAX_ITERATIONS
                    break
                    
            # If we completed all phases successfully
            if phase_success and phase_idx == len(self.config.phase_configs) - 1:
                self.status = WorkflowStatus.COMPLETED_SUCCESS
                
            # Finalize workflow
            self.workflow_logger.finalize(self.status.value)
            
        except Exception as e:
            self.status = WorkflowStatus.INCOMPLETE
            self.workflow_logger.finalize(self.status.value)
            raise e

    @property
    def current_phase(self) -> Optional[PhaseConfig]:
        """Get current phase configuration"""
        if 0 <= self._current_phase_idx < len(self.config.phase_configs):
            return self.config.phase_configs[self._current_phase_idx]
        return None
