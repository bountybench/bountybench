from abc import ABC, abstractmethod

class Response(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        return any('response' in B.__dict__ for B in subclass.__mro__)
    
    @abstractmethod
    def to_dict(self):
        pass