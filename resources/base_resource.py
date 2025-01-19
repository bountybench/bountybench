from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from functools import wraps
from typing import Dict, Any
from abc import ABC
import json
from messages.action_messages.action_message import ActionMessage
from messages.message import Message

@dataclass
class BaseResourceConfig(ABC):
    """
    Base configuration class for all resources.
    Provides common functionality for configuration management.
    """


    def __post_init__(self):
        """
        Automatically validate the configuration after initialization.
        """
        self.validate()
    
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

class BaseResource(ABC):
    @abstractmethod
    def stop(*args, **kwargs):
        pass

    def __init__(self, resource_id, resource_config):
        self._resource_id = resource_id
        self._resource_config = resource_config
        self._last_action_message = None

    def run(self, message: Message) -> ActionMessage:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    # if resource_id is relied on, then mandatory for all Resources
    @property
    def resource_id(self):
        return self._resource_id

    def __str__(self):
        return self._resource_id