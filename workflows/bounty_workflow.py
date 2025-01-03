from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from agents.agent_manager import AgentManager

from enum import Enum
import logging

# Import your specific modules and classes here
from phases.base_phase import BasePhase, PhaseConfig
from responses.base_response import BaseResponse
from resources.utils import docker_network_exists, read_bounty_metadata, read_repo_metadata, run_command
from utils.workflow_logger import workflow_logger
from workflows.base_workflow import WorkflowConfig

# Initialize the module-level logger
logger = logging.getLogger(__name__)


@dataclass
class BountyWorkflowConfig(WorkflowConfig):
    bounty_number: str
    repo_metadata: Dict[str, Any] = field(default_factory=dict)
    bounty_metadata: Dict[str, Any] = field(default_factory=dict)



class BountyWorkflow(ABC):
    """
    Base class for defining workflows that coordinate phases and their agents.
    Delegates resource management to individual phases.
    """

    def __init__(
        self,
        task_dir: Path,
        bounty_number: str,
        workflow_id: Optional[str] = "bounty_workflow",
        interactive: Optional[bool] = False
    ):
        """Initialize workflow with configuration"""
        self.bounty_number = str(bounty_number)  # Ensure it's a string
        self.interactive = interactive
        self.repo_metadata = read_repo_metadata(str(task_dir))
        self.bounty_metadata = read_bounty_metadata(str(task_dir), str(self.bounty_number))
        self.vulnerable_files: List[str] = []
        super().__init__(task_dir, workflow_id, interactive)
        self.setup_init()

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "repo_metadata": self.repo_metadata,
            "bounty_metadata": self.bounty_metadata
        }
        
    def setup_init(self) -> None:
        """Setup initial state of the workflow."""
        self.setup_network()
        self.setup_git_state()

    def setup_network(self) -> None:
        """Setup Docker network if it does not exist."""
        network_name = "shared_net"
        if not docker_network_exists(network_name):
            logger.info(f"Creating Docker network: {network_name}")
            run_command(["docker", "network", "create", network_name])
        else:
            logger.debug(f"Docker network '{network_name}' already exists.")

    def setup_git_state(self) -> None:
        """Setup Git state by checking out the vulnerable commit and identifying vulnerable files."""
        vulnerable_commit = self.bounty_metadata.get('vulnerable_commit', 'main')
        codebase_path = os.path.join(str(self.task_dir), "codebase")
        
        logger.info(f"Checking out vulnerable commit: {vulnerable_commit}")
        run_command(["git", "checkout", vulnerable_commit], codebase_path)
        
        for _, value in self.bounty_metadata.get('patch', {}).items():
            relative_path = os.path.relpath(value, start="codebase")
            full_path = os.path.join(str(self.task_dir), value)
            if os.path.exists(full_path):
                self.vulnerable_files.append(relative_path)
                logger.debug(f"Identified vulnerable file: {relative_path}")
        
        logger.info("Checking out main branch.")
        run_command(["git", "checkout", "main"], codebase_path)