import atexit
import re
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import List, Optional

from resources.base_resource import BaseResourceConfig
from resources.utils import run_command
from resources.base_setup_resource import BaseSetupResource
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

logger = get_main_logger(__name__)


@dataclass
class BountySetupResourceConfig(BaseResourceConfig):
    """Configuration for BountySetupResource"""

    task_dir: Path
    bounty_number: str

    def validate(self) -> None:
        """Validate Bounty Setup configuration"""
        if not self.task_dir.exists():
            raise ValueError(f"Invalid task_dir: {self.task_dir}")
        if not self.bounty_number:
            raise ValueError("Bounty number is required for bounty setup.")


class BountySetupResource(BaseSetupResource):
    """BountySetupResource for initializing and managing bounty-level containers."""

    def __init__(self, resource_id: str, config: BountySetupResourceConfig):
        # Call the superclass constructor first
        super().__init__(resource_id, config)

        # Set required properties
        self.task_dir = self._resource_config.task_dir
        self.bounty_number = self._resource_config.bounty_number
        self.role = "bounty_resource"
        self.setup_script_name = "setup_bounty_env.sh"
        
        # Initialize bounty directory
        self.bounty_dir = (
            self.task_dir
            / "bounties"
            / f"bounty_{self.bounty_number}"
        )
        
        # Set work_dir for bounty setup
        self.work_dir = self.bounty_dir / "setup_files"
        
        # Run the setup process
        self.setup()

    def to_dict(self) -> dict:
        """
        Serializes the BountySetupResource state to a dictionary.
        """
        return {
            "task_dir": str(self.task_dir),
            "bounty_dir": str(self.bounty_dir),
            "resource_id": self.resource_id,
            "role": self.role,
            "bounty_number": self.bounty_number,
            "container_names": self.container_names,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "BountySetupResource":
        """
        Creates a BountySetupResource instance from a serialized dictionary.
        """
        config = BountySetupResourceConfig(
            task_dir=Path(data["task_dir"]),
            bounty_number=data["bounty_number"],
        )
        instance = cls(data["resource_id"], config)
        instance.container_names = data["container_names"]
        return instance