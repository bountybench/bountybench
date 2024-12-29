from dataclasses import dataclass
from typing import Optional
import os
from resources.base_resource import BaseResourceConfig

@dataclass
class InitFilesResourceConfig(BaseResourceConfig):
    """Configuration for InitFilesResource"""
    task_repo_dir: str
    files_dir_name: str
    tmp_dir_name: str
    exploit_files_dir_name: Optional[str] = None
    vulnerable_commit: Optional[str] = None

    def validate(self) -> None:
        """Validate InitFiles configuration"""
        if not self.task_repo_dir or not os.path.exists(self.task_repo_dir):
            raise ValueError(f"Invalid task_repo_dir: {self.task_repo_dir}")
        if not self.files_dir_name:
            raise ValueError("files_dir_name cannot be empty")
        if not self.tmp_dir_name:
            raise ValueError("tmp_dir_name cannot be empty")
        if not self.tmp_dir_name:
            raise ValueError("tmp_dir_name cannot be empty")