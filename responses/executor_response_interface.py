from abc import ABC

class ExecutorResponseInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is ExecutorResponseInterface:           
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['command', 'response']
            )
        return NotImplemented

