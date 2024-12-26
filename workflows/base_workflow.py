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

    """
    Conceptually:
        1 Workflow - N Phases
        Worklow ~ Task ??
        A Workflow __ task
        solves? attempts?
        can a worklow attempt multiple tasks? 
        Will multiple workflows attempt a single task? Sounds wrong since we want to manage Resources / State at a workflow level

        So typically
        A workflow solves a single task
        But potentially many
        1: 1/N. But not N: 1 (never no future of this, vs N tasks could be supported potentially if shared resources etc.)
            for now, 1:1

        But actually...
        maybe not. Like I want to detect a new bounty
        I spin up N workers and then combine their efforts. This seems like a single task / find the best of them?

        Or are these Phases? And the Phases are distributed across machines? Probably easiest to just call them a Phase, and I can spin up N phases.

        How do Resources fit in?
            Workflows manage Resources

        A workflow solves a bounty

        Exploit (phase) + Patch  (phase) => Workflow for a task
    """

    def __init__(self, config: WorkflowConfig):
        """Initialize workflow with configuration"""
        self.config = config
        self.status = WorkflowStatus.INITIALIZED
        self._current_phase_idx = 0
        self._workflow_iteration_count = 0
        
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
            """ 
            Wait does this do all the setup at once? for resources etc. versus per agent of the workflow?

            e.g. 
            setup_resources: sets up all resources (K, T, P) at the beginning? Resource allocation should be per phase / as needed. 

            K (10) + T (6)= 16 GB
            total memory 18 GB
            P = 4 GB
            OOM


            Phase 1:
                K + T => 16GB
                Agent 1: Kali 
                Agent 2: Task Server
                Execute + Exploit 
            Release: T
            Phase 2:
                Allocate: P 
                Agent 1: Kali + Task Server
                Agent 3: Patch Server
                Execute + Patch

            Maybe can be bad now. But not horrible

            This is the magic of infra / workflow

            Workflow base class "invisbly" handles all the resource allocation, management, etc.

            If each atgent / phase defines the resouces it needs, the workflow will automagically handle all the resource allocations

            ALloca
            Malloc
            Free

            Resource.setup

            You have to fix now, because once workflows are written like this, hard refactor. 
            """
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

    """
    Update the code according to this comment: 
    Rather than just "run", you want to go phase by phase and use yield so that you can call next(workflow) and transition to run only a single phase. run can be an api where you continue runninguntil the end. This way you refactor the logic of running just a single phase vs running the netire workflow.
    """
    def run(self) -> None:
        """
        Execute the workflow by running phases in sequence.
        """
        try:
            self.setup_phases()
            self._validate_phase_configs()
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
