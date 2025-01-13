from abc import ABC

class CommandResponseInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is CommandResponseInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['command', 'observation', 'response']
            )
        return NotImplemented
