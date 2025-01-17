from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from functools import wraps
from typing import Dict, Any
from abc import ABC
import json
from messages.action_messages.action_message import ActionMessage


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
    
    @staticmethod
    def link_messages_decorator(func):
        """
        Decorator to handle linking of previous and next ActionMessages.
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> ActionMessage:
            # Call the original run method
            new_message = func(self, *args, **kwargs)

            if not isinstance(new_message, ActionMessage):
                raise TypeError("The run method must return an ActionMessage.")

            # Link the new message to the previous one
            if self._last_action_message:
                new_message.previous = self._last_action_message
                self._last_action_message.next = new_message

            # Update the last action message tracker
            self._last_action_message = new_message

            return new_message
        return wrapper
