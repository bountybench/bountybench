import abc
from typing import Optional

class CommandResponseInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is CommandResponseInterface:
            return any('command' in B.__dict__ for B in subclass.__mro__)
        return NotImplemented

def parse_field(field: str, case_sensitive:bool=False, stop_str:Optional[str]=None) -> str:
    """
    Takes in the name of a field and returns the field corresponding to that string using regex
    regex parses starting from field until the optional stop_str
    """
    pass

class SimpleCommandResponse:
    def __init__(self, response: str) -> None:
        self.response = response
 
    @property
    def response(self) -> str:
        return self.response

    @property
    def command(self) -> str:
        """
        either call
        parse_field('command')
        or do some metaprogramming i.e. get the name of the function and then pass that in automatically
        """
        return 'test'

class SimpleReflectResponse:
    def reflect(self) -> str:
        return 'test'

# class SimpleReflectResponse:
#     def command(self) -> str:
#         return 'test'



print(issubclass(SimpleCommandResponse, CommandResponseInterface))

print(issubclass(SimpleReflectResponse, CommandResponseInterface))

