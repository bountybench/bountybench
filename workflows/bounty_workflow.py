from resources.utils import read_bounty_metadata, read_repo_metadata
from workflow.utils import setup_shared_network
from workflows.base_workflow import BaseWorkflow

class BountyWorkflow(BaseWorkflow):
    def initialize(self):
        self.task_repo_dir = self.params['task_repo_dir']
        self.bounty_number = self.params['bounty_number']
        self.repo_metadata = read_repo_metadata(self.task_repo_dir)
        self.bounty_metadata = read_bounty_metadata(self.task_repo_dir, self.bounty_number)
        
        # Setup workflow config
        # config = BountyWorkflowConfig(
        #     id=workflow_id,
        #     max_iterations=25,
        #     logs_dir=Path("logs"),
        #     task_repo_dir=task_repo_dir,
        #     bounty_number=self.bounty_number,
        #     initial_prompt=self.get_initial_prompt(),
        #     metadata={
        #         "repo_metadata": self.repo_metadata,
        #         "bounty_metadata": self.bounty_metadata
        #     }
        # )

        # self.config = config

        # self.workflow_logger = workflow_logger
        # self.workflow_logger.initialize(
        #     workflow_name=config.id,
        #     logs_dir=str(config.logs_dir),
        #     task_repo_dir=str(config.task_repo_dir),
        #     bounty_number=str(config.bounty_number)
        # )

        # # Add workflow metadata
        # for key, value in config.metadata.items():
        #     self.workflow_logger.add_metadata(key, value)

        # Initialize additional attributes
        # self.vulnerable_files: List[str] = []

        setup_shared_network()

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

# @dataclass
# class BountyWorkflowConfig:
#     """Configuration for a workflow"""
#     id: str
#     max_iterations: int
#     logs_dir: Path
#     task_repo_dir: Path
#     bounty_number: int
#     initial_prompt: str
#     metadata: Dict[str, Any] = field(default_factory=dict)
#     phase_configs: List['PhaseConfig'] = field(default_factory=list)  

# class BountyWorkflow(BaseWorkflow):

#     def __init__(
#         self,
#         task_repo_dir: Path,
#         bounty_number: str,
#         workflow_id: Optional[str] = "base_workflow",
#         interactive: Optional[bool] = False
#     ):
#         super().__init__(workflow_id, interactive)
#         """Initialize workflow with configuration"""
#         self.task_repo_dir = task_repo_dir
#         self.bounty_number = str(bounty_number)  # Ensure it's a string
#         self.repo_metadata = read_repo_metadata(str(task_repo_dir))
#         self.bounty_metadata = read_bounty_metadata(str(task_repo_dir), str(self.bounty_number))
        
#         # Setup workflow config
#         config = BountyWorkflowConfig(
#             id=workflow_id,
#             max_iterations=25,
#             logs_dir=Path("logs"),
#             task_repo_dir=task_repo_dir,
#             bounty_number=self.bounty_number,
#             initial_prompt=self.get_initial_prompt(),
#             metadata={
#                 "repo_metadata": self.repo_metadata,
#                 "bounty_metadata": self.bounty_metadata
#             }
#         )

#         self.config = config

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

#     @property
#     def current_phase(self) -> Optional[PhaseConfig]:
#         """Get current phase configuration"""
#         if 0 <= self._current_phase_idx < len(self.config.phase_configs):
#             return self.config.phase_configs[self._current_phase_idx]
#         return None

#     def register_phase(self, phase: BasePhase):
#         phase_idx = len(self.phases)
#         phase.phase_config.phase_idx = phase_idx  # Set phase index
#         self.phases.append(phase)
#         logger.debug(f"Registered phase {phase_idx}: {phase.__class__.__name__}")