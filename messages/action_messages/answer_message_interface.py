from abc import ABC


class AnswerMessageInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is AnswerMessageInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ["answer", "message"]
            )
        return NotImplemented
