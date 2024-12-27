from dataclasses import dataclass
from typing import Optional
from resources.base_resource import BaseResourceConfig

@dataclass
class DockerResourceConfig(BaseResourceConfig):
    """Configuration for DockerResource"""

    def validate(self) -> None:
        """Validate Docker configuration"""
        pass
