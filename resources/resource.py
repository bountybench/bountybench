import re
from abc import ABC
from typing import Optional

class Resource(ABC):
    @abstractmethod
    def stop(args, kwargs)
