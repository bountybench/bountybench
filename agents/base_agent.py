from abc import ABC, abstractmethod
from typing import List
from responses.failure_response import FailureResponse
from responses.response import Response
from resources.resource_dict import resource_dict
from responses.response_history import ResponseHistory

class BaseAgent(ABC):
    def __init__(self, *args, **kwargs):
        self.resource_dict = resource_dict
        self.response_history = ResponseHistory()

        if hasattr(self, 'run') and kwargs.get('failure_detection', False):
            original_run = self.run

            def wrapped_run(responses: List[Response]) -> Response:
                # Call the original 'run' method
                new_response = original_run(responses)

                # Log the response
                self.response_history.log(new_response)

                # Check for repetition
                if self.response_history.is_repetitive(new_response):
                    # Handle repetition
                    new_response = FailureResponse("Repetitive response loop detected")

                return new_response

            self.run = wrapped_run

    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        pass