from abc import ABC

class Response(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        return any('response' in B.__dict__ for B in subclass.__mro__)