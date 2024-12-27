from dataclasses import dataclass
from typing import Optional
from resources.configs.base_resource_config import BaseResourceConfig

@dataclass
class DockerResourceConfig(BaseResourceConfig):
    """Configuration for DockerResource"""

    def validate(self) -> None:
        """Validate Docker configuration"""
        pass
