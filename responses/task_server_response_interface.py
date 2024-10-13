from responses.response import Response

class TaskServerResponseInterface(Response):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is TaskServerResponseInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['server_address', 'response']
            )
        return NotImplemented

