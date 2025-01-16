from abc import ABC, abstractmethod

class MessageInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        return all(
            any(attr in B.__dict__ for B in subclass.__mro__)
            for attr in ['message', 'prev', 'next']
        )
    
    @abstractmethod
    def to_dict(self):
        pass