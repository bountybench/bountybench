from abc import ABC, abstractmethod
from typing import Optional
from responses.executor_response_interface import ExecutorResponseInterface

class ActionResponseInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is ExecutorResponseInterface:           
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['command', 'answer']
            )
        return NotImplemented
    
    @property
    @abstractmethod
    def command(self) -> Optional[str]:
        pass
    
    @property
    @abstractmethod
    def answer(self) -> Optional[str]:
        pass