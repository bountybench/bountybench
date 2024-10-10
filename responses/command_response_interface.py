from responses.response import Response
from abc import abstractmethod

class CommandResponseInterface(Response):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is CommandResponseInterface:
            return any('command' in B.__dict__ for B in subclass.__mro__)
        return NotImplemented
    
    @property
    @abstractmethod
    def command(self) -> str:
        pass
