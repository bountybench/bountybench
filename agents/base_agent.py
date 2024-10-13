from abc import ABC, abstractmethod
from typing import List
from responses.response import Response
from resources.resource_dict import resource_dict

class BaseAgent(ABC):
    def __init__(self):
        self.resource_dict = resource_dict

    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        pass

