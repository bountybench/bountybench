from abc import ABC, abstractmethod
from typing import Optional
from responses.response import Response
from typing import List

class BaseAgent(ABC):
    def __init__(self, config):
        """
        Initialize the BaseAgent with configuration options.
        """
        self.config = config
            
    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        pass
    
    @abstractmethod
    def call_lm(self) -> Response:
        pass

    @abstractmethod
    def _handle_request(self, prompt: str) -> str:
        pass

    @abstractmethod
    def parse_response(self, lm_response: str) -> Response:
        pass