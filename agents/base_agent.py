from abc import ABC, abstractmethod
from typing import Optional
from responses.response import Response
from typing import List

class BaseAgent(ABC):
    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        pass

