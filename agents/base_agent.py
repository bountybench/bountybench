from abc import ABC, abstractmethod
import re
from typing import List
from responses.failure_response import FailureResponse
from responses.response import Response
from resources.resource_dict import resource_dict
from responses.response_history import ResponseHistory

class BaseAgent(ABC):
    def __init__(self, *args, **kwargs):
        self.resource_dict = resource_dict
        self.response_history = ResponseHistory()

        self._register_resources()

        if hasattr(self, 'run') and kwargs.get('failure_detection', False):
            original_run = self.run

            def wrapped_run(responses: List[Response]) -> Response:
                # Call the original 'run' method
                new_response = original_run(responses)

                # Check for repetition
                if self.response_history.is_repetitive(new_response):
                    # Handle repetition
                    new_response = FailureResponse("Repetitive response detected")
                else:
                    # Log the response
                    self.response_history.log(new_response)

                return new_response

            self.run = wrapped_run

    def _register_resources(self):
        """Registers required resources based on the inheriting class's needs."""
        required_resources = getattr(self, "REQUIRED_RESOURCES", [])

        for resource_type in required_resources:
            attr_name = '_'.join(word.lower() for word in re.findall(r'[A-Z][a-z]*|\d+', resource_type.__name__.split('Resource')[0]))

            try:
                setattr(self, attr_name, self._get_resource(resource_type))
            except KeyError as e:
                # Raise an error with the inheriting class's name
                raise RuntimeError(
                    f"Resource '{e.args[0]}' not set up. {self.__class__.__name__} cannot start."
                ) from e

    def _get_resource(self, resource_type):
        resource = self.resource_dict.get_item_of_resource_type(resource_type)
        if not resource:
            raise KeyError(f"{resource_type.__name__}")
        return resource
    
    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        pass