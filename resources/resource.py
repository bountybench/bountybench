import re
from abc import ABC
from typing import Optional

from abc import ABC, abstractmethod


class BaseResource(ABC):
    @abstractmethod
    def stop(args, kwargs):
        pass
