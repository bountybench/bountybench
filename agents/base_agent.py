from abc import ABC
from typing import Optional
from response_interfaces import Response
from resources.resource_manager import resource_manager

class BaseAgent(ABC):
    def __init__():
        self.resource_manager = resource_manager

    @abstract_method
    def run(self, responses: List[Response]) -> Response:
        pass

