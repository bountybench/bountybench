from abc import ABC

class ExtractionResponseInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is ExtractionResponseInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['proof', 'metadata', 'response']
            )
        return NotImplemented
