import atexit
import re
import time
from dataclasses import dataclass
from pathlib import Path

from resources.base_resource import BaseResourceConfig
from resources.utils import run_command
from resources.base_setup_resource import BaseSetupResource
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

logger = get_main_logger(__name__)


@dataclass
class RepoSetupResourceConfig(BaseResourceConfig):
    """Configuration for RepoSetupResource"""

    task_dir: Path

    def validate(self) -> None:
        """Validate Repo Setup configuration"""
        if not self.task_dir.exists():
            raise ValueError(f"Invalid task_dir: {self.task_dir}")


class RepoSetupResource(BaseSetupResource):
    """RepoSetupResource for initializing and managing task-level containers."""

    
    def __init__(self, resource_id: str, config: RepoSetupResourceConfig):
        # Call the superclass constructor first
        super().__init__(resource_id, config)

        # Set required properties
        self.task_dir = self._resource_config.task_dir
        self.role = "task_resource"
        self.setup_script_name = "setup_repo_env.sh"
        
        # Set work_dir for task setup (directly the task directory)
        self.work_dir = self.task_dir
        
        # Run the setup process
        self.setup()

    def to_dict(self) -> dict:
        """
        Serializes the RepoSetupResource state to a dictionary.
        """
        return {
            "task_dir": str(self.task_dir),
            "resource_id": self.resource_id,
            "role": self.role,
            "container_names": self.container_names,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "RepoSetupResource":
        """
        Creates a RepoSetupResource instance from a serialized dictionary.
        """
        config = RepoSetupResourceConfig(
            task_dir=Path(data["task_dir"]),
        )
        instance = cls(data["resource_id"], config)
        instance.container_names = data["container_names"]
        return instance