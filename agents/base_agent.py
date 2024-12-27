from abc import ABC, abstractmethod
import re
from typing import List, Optional, Set, Tuple, Union

from resources.base_resource import BaseResource
from responses.failure_response import FailureResponse
from responses.response import Response
from responses.response_history import ResponseHistory
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class BaseAgent(ABC):
    """
    Base class for agents that declares REQUIRED_RESOURCES, OPTIONAL_RESOURCES, etc.
    Instead of directly creating or finding resources in resource_dict, it fetches
    them from the resource_manager, which is responsible for the resource lifecycle.
    """

    REQUIRED_RESOURCES: List[Union[str, Tuple[BaseResource, str]]] = []
    OPTIONAL_RESOURCES: List[Union[str, Tuple[BaseResource, str]]] = []
    ACCESSIBLE_RESOURCES: List[Union[str, Tuple[BaseResource, str]]] = []

    def __init__(self, resource_manager=None, *args, **kwargs):
        """
        Args:
            resource_manager: An instance of ResourceManager, which can provide .get_resource(resource_id).
            failure_detection: Whether or not to wrap the run() method with repetitive-response checks.
        """
        self.resource_manager = resource_manager
        self.response_history = ResponseHistory()
        self.target_host_address = kwargs.get("target_host", "")

        # We do NOT call _register_resources() here. Instead, we wait until
        # the user calls `initialize_resources()` after ResourceManager has allocated them.

        # Optional: Wrap the `run` method for failure detection
        if hasattr(self, "run") and kwargs.get("failure_detection", False):
            original_run = self.run

            def wrapped_run(responses: List[Response]) -> Response:
                new_response = original_run(responses)
                if self.response_history.is_repetitive(new_response):
                    new_response = FailureResponse("Repetitive response detected")
                else:
                    self.response_history.log(new_response)
                return new_response

            self.run = wrapped_run

    @classmethod
    def get_required_resources(cls) -> Set[str]:
        return cls.REQUIRED_RESOURCES
    
    def initialize_resources(self):
        """
        Public method to fetch and attach required/optional resources as attributes on the agent.
        Call this AFTER the ResourceManager has allocated them for the relevant phase.
        """
        required_resources = getattr(self, "REQUIRED_RESOURCES", [])
        optional_resources = getattr(self, "OPTIONAL_RESOURCES", [])
        accessible_resources = getattr(self, "ACCESSIBLE_RESOURCES", [])

        # Bind required resources
        for resource_entry in required_resources:
            self._bind_resource_to_agent(resource_entry, optional=False)

        # Bind optional resources (set to None if not found)
        for resource_entry in optional_resources:
            try:
                self._bind_resource_to_agent(resource_entry, optional=True)
            except KeyError:
                # Resource not allocated? Just set to None
                if isinstance(resource_entry, tuple):
                    _, resource_id = resource_entry
                    attr_name = resource_id
                else:
                    attr_name = resource_entry
                setattr(self, attr_name, None)
                logger.warning(f"Optional resource '{attr_name}' not available. Setting to None.")

        # Check that ACCESSIBLE_RESOURCES is subset of (REQUIRED + OPTIONAL)
        all_declared = set(required_resources) | set(optional_resources)
        accessible_set = set(accessible_resources)
        declared_strings = {self._entry_to_str(e) for e in all_declared}
        accessible_strings = {self._entry_to_str(e) for e in accessible_set}
        missing = accessible_strings - declared_strings
        if missing:
            raise ValueError(
                f"{self.__class__.__name__} ACCESSIBLE_RESOURCES must be a subset of "
                f"REQUIRED_RESOURCES + OPTIONAL_RESOURCES. Missing: {missing}"
            )

    def _bind_resource_to_agent(self, resource_entry: Union[str, Tuple[BaseResource, str]], optional: bool):
        """
        Fetch the resource from resource_manager and set it as an attribute on the agent.
        resource_entry can be:
          - "kali_env" (a string resource_id), or
          - (KaliEnvResource, "kali_env") if you prefer that notation.
        """
        if isinstance(resource_entry, tuple):
            # e.g. (KaliEnvResource, "kali_env") => resource_id = "kali_env"
            _, resource_id = resource_entry
        else:
            resource_id = resource_entry

        if not self.resource_manager:
            # If no resource_manager, we can't fetch resources
            if optional:
                setattr(self, resource_id, None)
                return
            raise RuntimeError(f"Agent '{self.__class__.__name__}' has no resource_manager set.")

        try:
            resource_instance = self.resource_manager.get_resource(resource_id)
            setattr(self, resource_id, resource_instance)
        except KeyError:
            if optional:
                setattr(self, resource_id, None)
                logger.debug(f"Optional resource '{resource_id}' not found. Setting to None.")
            else:
                raise

    def _entry_to_str(self, entry: Union[str, Tuple[BaseResource, str]]) -> str:
        """
        Convert either "kali_env" or (KaliEnvResource, "kali_env") into "kali_env".
        """
        if isinstance(entry, tuple):
            return entry[1]
        return entry

    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        """
        Must be implemented by inheriting classes.
        Process input responses and return a new Response.
        """
        pass