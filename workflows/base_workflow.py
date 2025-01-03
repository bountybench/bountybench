from abc import ABC

from pyparsing import abstractmethod


class BaseWorkflow(ABC):
    def __init__(self, **kwargs):
        self.params = kwargs
        self.initialize()
        self.create_phases()
        self._compute_resource_schedule()

    @abstractmethod
    def create_phases(self):
        pass

    @abstractmethod
    def get_initial_prompt(self):
        pass

    def initialize(self):
        pass

    def run():
        pass

    def run_phases():
        pass

    def setup_phase():
        pass

    def _compute_resource_schedule(self):
        pass

# from abc import ABC, abstractmethod
# from dataclasses import dataclass, field
# import os
# from pathlib import Path
# from typing import Any, Dict, List, Optional
# from agents.agent_manager import AgentManager

# from enum import Enum
# import logging

# # Import your specific modules and classes here
# from phases.base_phase import BasePhase, PhaseConfig
# from responses.base_response import BaseResponse
# from resources.utils import docker_network_exists, read_bounty_metadata, read_repo_metadata, run_command
# from utils.workflow_logger import workflow_logger

# # Initialize the module-level logger
# logger = logging.getLogger(__name__)

# class WorkflowStatus(Enum):
#     """Status of workflow execution"""
#     INITIALIZED = "initialized"
#     INCOMPLETE = "incomplete"
#     COMPLETED_SUCCESS = "completed_success"
#     COMPLETED_FAILURE = "completed_failure"
#     COMPLETED_MAX_ITERATIONS = "completed_max_iterations"


# @dataclass
# class WorkflowConfig:
#     """Configuration for a workflow"""
#     id: str
#     max_iterations: int
#     logs_dir: Path
#     initial_prompt: str
#     metadata: Dict[str, Any] = field(default_factory=dict)
#     phase_configs: List['PhaseConfig'] = field(default_factory=list)  



# class BaseWorkflow(ABC):
#     """
#     Base class for defining workflows that coordinate phases and their agents.
#     Delegates resource management to individual phases.
#     """

#     def __init__(
#         self,
#         workflow_id: Optional[str] = "base_workflow",
#         interactive: Optional[bool] = False
#     ):
#         """Initialize workflow with configuration"""
#         self.interactive = interactive
        
#         # Setup workflow config
#         config = WorkflowConfig(
#             id=workflow_id,
#             max_iterations=25,
#             logs_dir=Path("logs"),
#             initial_prompt=self.get_initial_prompt(),
#             metadata={
#             }
#         )

#         self.config = config
#         self.status = WorkflowStatus.INITIALIZED
#         self._current_phase_idx = 0
#         self._workflow_iteration_count = 0

#         self.workflow_logger = workflow_logger
#         self.workflow_logger.initialize(
#             workflow_name=config.id,
#             logs_dir=str(config.logs_dir),
#             task_repo_dir=str(config.task_repo_dir),
#             bounty_number=str(config.bounty_number)
#         )

#         # Add workflow metadata
#         for key, value in config.metadata.items():
#             self.workflow_logger.add_metadata(key, value)

#         # Initialize ResourceManager
#         self.agent_manager = AgentManager()

#         # Initialize tracking structures
#         self.phases: List[BasePhase] = []       # List to store phase instances
#         self.phase_class_map = {}

#         # Initialize additional attributes
#         self.vulnerable_files: List[str] = []

#         # Setup workflow
#         self.setup_init()
#         self.create_phases() # To be implemented by subclasses
#         self._compute_resource_schedule()

#     @abstractmethod
#     def get_initial_prompt(self) -> str:
#         """Provide the initial prompt for the workflow."""
#         pass

#     @abstractmethod
#     def create_phases(self):
#         """Create and register phases. To be implemented by subclasses."""
#         pass

#     def _compute_resource_schedule(self) -> None:
#         """
#         Compute the agent (which will compute resource) schedule across all phases.
#         """
#         phase_classes = [type(phase) for phase in self.phases]
#         self.agent_manager.compute_resource_schedule(phase_classes)
#         logger.debug("Computed resource schedule for all phases based on agents.")

#     def setup_phase(self, phase_idx: int, initial_response: Optional[BaseResponse] = None) -> BasePhase:
#         """
#         Setup and run a specific phase.

#         Args:
#             phase_idx (int): The index of the phase to set up.
#             initial_response (Optional[BaseResponse]): The initial response for the phase.

#         Returns:
#             BasePhase: The phase instance.
#         """
#         try:
#             phase_instance = self.phases[phase_idx]

#             logger.info(f"Setting up phase {phase_idx}: {phase_instance.__class__.__name__}")

#             if initial_response:
#                 phase_instance.initial_response = initial_response
#                 logger.info(f"Set initial response for phase {phase_idx}")
#             else:
#                 logger.info(f"No initial response provided for phase {phase_idx}")
#             # Setup the phase
#             phase_instance.setup()

#             return phase_instance

#         except Exception as e:
#             self.status = WorkflowStatus.INCOMPLETE
#             logger.error(f"Failed to set up phase {phase_idx}: {e}")
#             raise

#     def run_phases(self):
#         """
#         Execute all phases in sequence.
#         Yields:
#             Tuple[BaseResponse, bool]: The response from each phase and a success flag.
#         """
#         try:
#             self.status = WorkflowStatus.INCOMPLETE
#             prev_response = BaseResponse(self.config.initial_prompt) if self.config.initial_prompt else None

#             for phase_idx, phase in enumerate(self.phases):
#                 self._current_phase_idx = phase_idx

#                 # Setup and run the phase
#                 phase_instance = self.setup_phase(phase_idx, prev_response)
#                 phase_response, phase_success = phase_instance.run_phase()
                
#                 logger.info(f"Phase {phase_idx} completed: {phase_instance.__class__.__name__} with success={phase_success}")

#                 # Update workflow state
#                 prev_response = phase_response
#                 if not phase_success:
#                     self.status = WorkflowStatus.COMPLETED_FAILURE
#                     yield phase_response, phase_success
#                     break

#                 self._workflow_iteration_count += 1
#                 if self._workflow_iteration_count >= self.config.max_iterations:
#                     self.status = WorkflowStatus.COMPLETED_MAX_ITERATIONS
#                     yield phase_response, phase_success
#                     break

#                 # Yield current phase results
#                 yield phase_response, phase_success

#                 # Resources are already handled within the phase

#             else:
#                 # If all phases completed successfully
#                 self.status = WorkflowStatus.COMPLETED_SUCCESS

#             # Finalize workflow
#             self.workflow_logger.finalize(self.status.value)

#         except Exception as e:
#             self.status = WorkflowStatus.INCOMPLETE
#             self.workflow_logger.finalize(self.status.value)
#             raise e

#     def run(self) -> None:
#         """
#         Execute the entire workflow by running all phases in sequence.
#         This is a convenience method that runs the workflow to completion.
#         """
#         # Run through all phases
#         for _ in self.run_phases():
#             continue

#     @property
#     def current_phase(self) -> Optional[PhaseConfig]:
#         """Get current phase configuration"""
#         if 0 <= self._current_phase_idx < len(self.config.phase_configs):
#             return self.config.phase_configs[self._current_phase_idx]
#         return None

#     def setup_init(self) -> None:
#         """Setup initial state of the workflow."""
#         self.setup_network()
#         self.setup_git_state()

#     def setup_network(self) -> None:
#         """Setup Docker network if it does not exist."""
#         network_name = "shared_net"
#         if not docker_network_exists(network_name):
#             logger.info(f"Creating Docker network: {network_name}")
#             run_command(["docker", "network", "create", network_name])
#         else:
#             logger.debug(f"Docker network '{network_name}' already exists.")

#     def setup_git_state(self) -> None:
#         """Setup Git state by checking out the vulnerable commit and identifying vulnerable files."""
#         vulnerable_commit = self.bounty_metadata.get('vulnerable_commit', 'main')
#         codebase_path = os.path.join(str(self.task_repo_dir), "codebase")
        
#         logger.info(f"Checking out vulnerable commit: {vulnerable_commit}")
#         run_command(["git", "checkout", vulnerable_commit], codebase_path)
        
#         for _, value in self.bounty_metadata.get('patch', {}).items():
#             relative_path = os.path.relpath(value, start="codebase")
#             full_path = os.path.join(str(self.task_repo_dir), value)
#             if os.path.exists(full_path):
#                 self.vulnerable_files.append(relative_path)
#                 logger.debug(f"Identified vulnerable file: {relative_path}")
        
#         logger.info("Checking out main branch.")
#         run_command(["git", "checkout", "main"], codebase_path)

#     def register_phase(self, phase: BasePhase):
#         phase_idx = len(self.phases)
#         phase.phase_config.phase_idx = phase_idx  # Set phase index
#         self.phases.append(phase)
#         logger.debug(f"Registered phase {phase_idx}: {phase.__class__.__name__}")