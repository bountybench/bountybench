from abc import ABC
from typing import Optional

class Response(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is CommandResponseInterface:
            return any('response' in B.__dict__ for B in subclass.__mro__)
        return NotImplemented

def parse_field(field: str, case_sensitive:bool=False, stop_str:Optional[str]=None) -> str:
    """
    Takes in the name of a field and returns the field corresponding to that string using regex
    regex parses starting from field until the optional stop_str
    """
    pass

