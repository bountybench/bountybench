from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List
from phases.base_phase import PhaseConfig
from resources.utils import read_bounty_metadata, read_repo_metadata
from utils.workflow_logger import workflow_logger
from workflows.utils import setup_shared_network
from workflows.base_workflow import BaseWorkflow

@dataclass
class BountyWorkflowConfig:
    """Configuration for a workflow"""
    id: str
    max_iterations: int
    logs_dir: Path
    task_repo_dir: Path
    bounty_number: int
    initial_prompt: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class BountyWorkflow(BaseWorkflow, ABC):
    def _initialize(self):
        self.workflow_id = self.params['workflow_id']
        self.task_repo_dir = self.params['task_repo_dir']
        self.bounty_number = self.params['bounty_number']
        self.repo_metadata = read_repo_metadata(str(self.task_repo_dir))
        self.bounty_metadata = read_bounty_metadata(str(self.task_repo_dir), self.bounty_number)
        
        # Setup workflow config
        config = BountyWorkflowConfig(
            id=self.workflow_id,
            max_iterations=25,
            logs_dir=Path("logs"),
            task_repo_dir=self.task_repo_dir,
            bounty_number=self.bounty_number,
            initial_prompt=self._get_initial_prompt(),
            metadata={
                "repo_metadata": self.repo_metadata,
                "bounty_metadata": self.bounty_metadata
            }
        )

        self.config = config

        self.workflow_logger = workflow_logger
        self.workflow_logger.initialize(
            workflow_name=config.id,
            logs_dir=str(config.logs_dir),
            task_repo_dir=str(config.task_repo_dir),
            bounty_number=str(config.bounty_number)
        )

        # Add workflow metadata
        for key, value in config.metadata.items():
            self.workflow_logger.add_metadata(key, value)

        setup_shared_network()