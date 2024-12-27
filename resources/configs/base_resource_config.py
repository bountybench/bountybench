from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from abc import ABC
import json

@dataclass
class BaseResourceConfig(ABC):
    """
    Base configuration class for all resources.
    Provides common functionality for configuration management.
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.
        """
        return asdict(self)

    def to_json(self) -> str:
        """
        Convert the configuration to a JSON string.
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseResourceConfig':
        """
        Create a configuration instance from a dictionary.
        """
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'BaseResourceConfig':
        """
        Create a configuration instance from a JSON string.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def validate(self) -> None:
        """
        Validate the configuration.
        Subclasses should override this method to add specific validation rules.
        Raises ValueError if validation fails.
        """
        pass