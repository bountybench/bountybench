from abc import ABC, abstractmethod
import re
from typing import List, Optional, Tuple, Union

from resources.base_resource import BaseResource
from responses.failure_response import FailureResponse
from responses.response import Response
from responses.response_history import ResponseHistory
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class BaseAgent(ABC):
    REQUIRED_RESOURCES: List[Union[str, Tuple[BaseResource, str]]] = []
    OPTIONAL_RESOURCES: List[Union[str, Tuple[BaseResource, str]]] = []
    ACCESSIBLE_RESOURCES: List[Union[str, Tuple[BaseResource, str]]] = []

    def __init__(self, resource_manager=None, *args, **kwargs):
        """
        We do NOT fetch resources here. We'll do that in register_resources() 
        once we're sure they've been allocated by ResourceManager.
        """
        self.resource_manager = resource_manager
        self.response_history = ResponseHistory()
        self.target_host_address = kwargs.get("target_host", "")

        # Optional: wrap run(...) for failure detection
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

    def register_resources(self):
        """
        Binds required and optional resources from the ResourceManager.
        If an optional resource is missing, we simply do NOT create the attribute 
        (rather than setting it to None).
        """
        if not self.resource_manager:
            raise RuntimeError(
                f"Agent '{self.__class__.__name__}' has no resource_manager set; "
                "cannot fetch resources."
            )

        required = getattr(self, "REQUIRED_RESOURCES", [])
        optional = getattr(self, "OPTIONAL_RESOURCES", [])
        accessible = getattr(self, "ACCESSIBLE_RESOURCES", [])

        # 1) Bind required resources
        for entry in required:
            self._bind_resource(entry, optional=False)

        # 2) Bind optional resources
        #    If a KeyError is thrown, skip creating the attribute
        for entry in optional:
            try:
                self._bind_resource(entry, optional=True)
            except KeyError:
                if isinstance(entry, tuple):
                    _, resource_id = entry
                    logger.warning(f"Optional resource '{resource_id}' not allocated. Omitting attribute.")
                else:
                    logger.warning(f"Optional resource '{entry}' not allocated. Omitting attribute.")
                # DO NOT create the attribute if missing

        # 3) Check that ACCESSIBLE_RESOURCES is a subset of (REQUIRED + OPTIONAL)
        declared = set(required) | set(optional)
        declared_ids = {self._entry_to_str(e) for e in declared}
        accessible_ids = {self._entry_to_str(e) for e in accessible}
        missing = accessible_ids - declared_ids
        if missing:
            raise ValueError(
                f"{self.__class__.__name__}: ACCESSIBLE_RESOURCES must be a subset "
                f"of REQUIRED + OPTIONAL. Missing: {missing}"
            )

    def _bind_resource(
        self,
        entry: Union[str, Tuple[BaseResource, str]],
        optional: bool,
    ):
        """
        Fetch the resource from resource_manager, and create an attribute if found.
        If 'optional' is False and the resource is missing, raise KeyError.
        If 'optional' is True and the resource is missing, raise KeyError 
        (caught by caller to skip creating the attribute).
        """
        if isinstance(entry, tuple):
            _, resource_id = entry
        else:
            resource_id = entry

        resource_instance = self.resource_manager.get_resource(resource_id)
        setattr(self, resource_id, resource_instance)

    def _entry_to_str(self, entry: Union[str, Tuple[BaseResource, str]]) -> str:
        """Convert either 'kali_env' or (KaliEnvResource, 'kali_env') into 'kali_env'."""
        if isinstance(entry, tuple):
            return entry[1]
        return entry

    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        """
        Subclasses must implement how they handle input responses
        and produce a new response.
        """
        pass