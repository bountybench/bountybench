from abc import ABC
from typing import Optional

class ExecutorResponseInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is ExecutorResponseInterface:
            return any(
                'command' in B.__dict__ for B in subclass.__mro__
                 and 'response' in B.__dict__ for B in subclass.__mro__
                 and 'observation' in B.__dict__ for B in subclass.__mro__
            )
        return NotImplemented

