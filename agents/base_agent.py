from abc import ABC, abstractmethod
import re
from typing import List, Optional, Tuple, Type, Union
from resources.resource_dict import resource_dict
from resources.base_resource import BaseResource
from responses.failure_response import FailureResponse
from responses.response import Response
from responses.response_history import ResponseHistory
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class BaseAgent(ABC):
    """
    Base class for agents, with support for required, accessible, and optional resources.
    Handles resource registration and ensures accessible resources are a subset of required or optional resources.
    """

    def __init__(self, resource_manager=None, *args, **kwargs):
        self.resource_dict = resource_dict
        self.resource_manager = resource_manager  # Store resource manager reference
        self.response_history = ResponseHistory()
        self.target_host_address = kwargs.get("target_host", "")

        self._register_resources_with_manager()


        # Wrap the `run` method for failure detection if needed
        if hasattr(self, 'run') and kwargs.get('failure_detection', False):
            original_run = self.run

            def wrapped_run(responses: List[Response]) -> Response:
                new_response = original_run(responses)
                if self.response_history.is_repetitive(new_response):
                    new_response = FailureResponse("Repetitive response detected")
                else:
                    self.response_history.log(new_response)
                return new_response

            self.run = wrapped_run

    def _register_resources_with_manager(self):
        """
        Registers resources using the ResourceManager approach.
        Resources will be created on-demand when phases are activated.
        """
        required_resources = getattr(self, "REQUIRED_RESOURCES", [])
        accessible_resources = getattr(self, "ACCESSIBLE_RESOURCES", [])
        optional_resources = getattr(self, "OPTIONAL_RESOURCES", [])

        # Register placeholders for required resources
        for resource_entry in required_resources:
            if isinstance(resource_entry, tuple):
                resource_type, role = resource_entry
                setattr(self, role, None)  # Will be set when phase is activated
            else:
                attr_name = self._generate_attr_name(resource_entry)
                setattr(self, attr_name, None)  # Will be set when phase is activated

        # Register placeholders for optional resources
        for resource_entry in optional_resources:
            if isinstance(resource_entry, tuple):
                _, role = resource_entry
                setattr(self, role, None)
            else:
                attr_name = self._generate_attr_name(resource_entry)
                setattr(self, attr_name, None)

        # Ensure accessible_resources are a subset of required_resources + optional_resources
        accessible_types = {entry[0] if isinstance(entry, tuple) else entry for entry in accessible_resources}
        all_types = {entry[0] if isinstance(entry, tuple) else entry for entry in (required_resources + optional_resources)}
        if not accessible_types.issubset(all_types):
            raise ValueError(f"{self.__class__.__name__} ACCESSIBLE_RESOURCES must be a subset of REQUIRED_RESOURCES and OPTIONAL_RESOURCES.")


    def _get_resource(self, resource_type, role: Optional[str] = None, optional: bool = False):
        if self.resource_manager is not None:
            try:
                if role:
                    return self.resource_manager.get_resource((resource_type, role))
                return self.resource_manager.get_resource(resource_type)
            except ValueError:
                if optional:
                    return None
                raise KeyError(f"No resource of type {resource_type.__name__} found")
        else:
            resources = self.resource_dict.get_items_of_resource_type(resource_type)
            if not resources:
                if optional:
                    return None
                raise KeyError(f"No resource of type {resource_type.__name__} found")
            
            if role:
                for resource in resources:
                    if hasattr(resource, 'role') and resource.role == role:
                        return resource
                if optional:
                    return None
                raise KeyError(f"No resource of type {resource_type.__name__} with role '{role}' found")
            
            return resources[0]

    @staticmethod
    def _generate_attr_name(resource_type) -> str:
        """Generates a snake_case attribute name for a resource type."""
        return '_'.join(word.lower() for word in re.findall(r'[A-Z][a-z]*|\d+', resource_type.__name__.split('Resource')[0]))

    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        """
        Abstract method to be implemented by inheriting classes.
        This method processes a list of responses and returns a new response.
        """
        pass