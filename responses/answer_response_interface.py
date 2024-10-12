from responses.response import Response

class AnswerResponseInterface(Response):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is AnswerResponseInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['answer', 'response']
            )
        return NotImplemented