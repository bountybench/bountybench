from abc import ABC, abstractmethod
from responses.action_response import ActionType

class ExecutorResponseInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is ExecutorResponseInterface:           
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['action', 'response']
            )
        return NotImplemented

    @property
    @abstractmethod
    def action(self) -> ActionType:
        pass
    
    @property
    @abstractmethod
    def response(self) -> str:
        pass
