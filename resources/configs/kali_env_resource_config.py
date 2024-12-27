from dataclasses import dataclass
from typing import Dict, Optional
import os
from resources.configs.base_resource_config import BaseResourceConfig

@dataclass
class KaliEnvResourceConfig(BaseResourceConfig):
    """Configuration for KaliEnvResource"""
    task_repo_dir: Optional[str] = None
    bounty_number: Optional[str] = None
    volumes: Optional[Dict[str, Dict[str, str]]] = None

    def validate(self) -> None:
        """Validate KaliEnv configuration"""
        if self.task_repo_dir and not os.path.exists(self.task_repo_dir):
            raise ValueError(f"Invalid task_repo_dir: {self.task_repo_dir}")
        if self.volumes:
            for host_path in self.volumes.keys():
                if not os.path.exists(host_path):
                    raise ValueError(f"Invalid volume host path: {host_path}")