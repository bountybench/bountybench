from abc import ABC
from typing import Optional
from responses.response import Response

class BaseAgent(ABC):
    @abstract_method
    def run(self, responses: List[Response]) -> Response:
        pass

