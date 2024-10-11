from abc import ABC

class CommandResponseInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is CommandResponseInterface:
            return any('command' in B.__dict__ for B in subclass.__mro__)
        return NotImplemented

