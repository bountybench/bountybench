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
        We do NOT fetch resources here. We'll do that in bind_resources_strict() once
        we're sure they've been allocated by ResourceManager.
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
        'Strict environment' binding: must be called AFTER the ResourceManager has allocated
        the resources for this agent's phase. If any required resource is missing, KeyError is raised.
        """
        if not self.resource_manager:
            raise RuntimeError(
                f"Agent '{self.__class__.__name__}' has no resource_manager set; cannot fetch resources."
            )

        required = getattr(self, "REQUIRED_RESOURCES", [])
        optional = getattr(self, "OPTIONAL_RESOURCES", [])
        accessible = getattr(self, "ACCESSIBLE_RESOURCES", [])

        # 1) Bind required
        for entry in required:
            self._bind_resource(entry, optional=False)

        # 2) Bind optional
        for entry in optional:
            try:
                self._bind_resource(entry, optional=True)
            except KeyError:
                # set to None if not found
                if isinstance(entry, tuple):
                    _, rid = entry
                    attr_name = rid
                else:
                    attr_name = entry
                setattr(self, attr_name, None)
                logger.warning(f"Optional resource '{attr_name}' not allocated. Setting to None.")

        # 3) Check accessibility subset
        declared = set(required) | set(optional)
        declared_ids = {self._entry_to_str(e) for e in declared}
        accessible_ids = {self._entry_to_str(e) for e in accessible}
        missing = accessible_ids - declared_ids
        if missing:
            raise ValueError(
                f"{self.__class__.__name__}: ACCESSIBLE_RESOURCES must be a subset of "
                f"REQUIRED + OPTIONAL. Missing: {missing}"
            )

    def _bind_resource(self, entry: Union[str, Tuple[BaseResource, str]], optional: bool):
        if isinstance(entry, tuple):
            _, resource_id = entry
        else:
            resource_id = entry
        
        # fetch from resource_manager, strict => KeyError if missing
        resource_instance = self.resource_manager.get_resource(resource_id)
        setattr(self, resource_id, resource_instance)

    def _entry_to_str(self, entry: Union[str, Tuple[BaseResource, str]]) -> str:
        """Convert either 'kali_env' or (KaliEnvResource, 'kali_env') into 'kali_env'."""
        if isinstance(entry, tuple):
            return entry[1]
        return entry

    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        pass