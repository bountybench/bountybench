from abc import ABC

class ActionMessageInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is ActionMessageInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['resource_id']
            )
        return NotImplemented