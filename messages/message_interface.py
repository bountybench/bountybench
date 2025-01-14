from abc import ABC, abstractmethod

class MessageInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        return any('message' in B.__dict__ for B in subclass.__mro__)
    
    @abstractmethod
    def to_dict(self):
        pass