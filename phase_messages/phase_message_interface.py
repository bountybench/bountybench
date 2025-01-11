from abc import ABC, abstractmethod

class PhaseMessageInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        return all(
            any(attr in B.__dict__ for B in subclass.__mro__)
            for attr in ['agent_messages', 'success', 'complete']
        )
    
    @abstractmethod
    def to_dict(self):
        pass