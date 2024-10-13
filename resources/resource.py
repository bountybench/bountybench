import re
from abc import ABC, abstractmethod
from typing import Optional

#note to self / others. Base for abstracting / ABC and no Base for interfaces since don't need to implement
# Base is a keyword for people to be aware of since they need to explicilty inherit vs implicity things are handled
class BaseResource(ABC):
    resource_id: str

    @abstractmethod
    def stop(args, kwargs):
        pass
