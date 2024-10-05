from abc import ABC
from typing import Optional

class AgentBase(ABC):
    @abstract_method
    def run(self, responses: List[Response]) -> Response:
        pass

