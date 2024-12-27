from dataclasses import dataclass
from typing import Dict, Optional
import os
from resources.configs.base_resource_config import BaseResourceConfig

@dataclass
class SetupResourceConfig(BaseResourceConfig):
    """Configuration for SetupResource"""
    task_level_setup: bool
    task_repo_dir: str
    files_dir: str
    bounty_number: Optional[str] = None
    server_address: Optional[str] = None

    def validate(self) -> None:
        """Validate Setup configuration"""
        if not os.path.exists(self.task_repo_dir):
            raise ValueError(f"Invalid task_repo_dir: {self.task_repo_dir}")
        if not os.path.exists(self.files_dir):
            raise ValueError(f"Invalid files_dir: {self.files_dir}")
        if self.server_address and ":" not in self.server_address:
            raise ValueError(f"Invalid server_address format: {self.server_address}")