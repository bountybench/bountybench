from abc import ABC


class CommandMessageInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is CommandMessageInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ["command", "message"]
            )
        return NotImplemented
