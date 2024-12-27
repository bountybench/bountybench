from abc import ABC, abstractmethod
import re
from typing import List, Optional, Set, Tuple, Union

from resources.base_resource import BaseResource
from responses.failure_response import FailureResponse
from responses.response import Response
from responses.response_history import ResponseHistory
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class AgentConfig:
    id: str

class BaseAgent(ABC):
    """
    A base agent that automatically binds resources from a ResourceManager.
    Resource references can be declared in three lists:
      1) REQUIRED_RESOURCES  -> must exist, or KeyError is raised
      2) OPTIONAL_RESOURCES  -> if missing, attribute is omitted (no exception)
      3) ACCESSIBLE_RESOURCES -> must be subset of (required+optional).
    
    Each list entry can be:
      - A resource class (e.g. DockerResource)
      - A tuple (ResourceClass, "custom_attr_name")
    
    If only a class is given, `_generate_attr_name` is used to create a Python
    attribute name automatically (e.g. DockerResource -> "docker_resource").
    For optional resources, if not found, the attribute is *omitted* (not None).
    """

    # By default, these lists can be either a class or (class, "string").
    REQUIRED_RESOURCES: List[Union[type, Tuple[type, str]]] = []
    OPTIONAL_RESOURCES: List[Union[type, Tuple[type, str]]] = []
    ACCESSIBLE_RESOURCES: List[Union[type, Tuple[type, str]]] = []

    def __init__(self, agent_config: AgentConfig, resource_manager=None):
        """
        We do NOT fetch resources here. We'll do that in `register_resources()` 
        once we know they've been allocated by the ResourceManager.
        
        If `failure_detection=True` is passed, we wrap `run()` to detect repetitive responses.
        """
        self.resource_manager = resource_manager
        self.response_history = ResponseHistory()
        self.agent_config = agent_config
        self.target_host_address = getattr(self.agent_config, "target_host", "")

        # We do NOT call _register_resources() here. Instead, we wait until
        # the user calls `initialize_resources()` after ResourceManager has allocated them.

        # Optional: wrap the run(...) method for failure detection
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
    
    def register_resources(self):
        """
        Binds required and optional resources from the ResourceManager.
        
        - For required resources: raises KeyError if missing.
        - For optional resources: if missing, we omit the attribute entirely
          (rather than setting it to None).
        - Ensures ACCESSIBLE_RESOURCES is a subset of (REQUIRED_RESOURCES + OPTIONAL_RESOURCES).
        """
        if not self.resource_manager:
            raise RuntimeError(
                f"Agent '{self.__class__.__name__}' has no resource_manager set; "
                "cannot fetch resources."
            )

        required = getattr(self, "REQUIRED_RESOURCES", [])
        optional = getattr(self, "OPTIONAL_RESOURCES", [])
        accessible = getattr(self, "ACCESSIBLE_RESOURCES", [])

        # 1) Bind required resources (KeyError if missing)
        for entry in required:
            self._bind_resource(entry, optional=False)

        # 2) Bind optional resources (skip if KeyError)
        for entry in optional:
            try:
                self._bind_resource(entry, optional=True)
            except KeyError:
                # Omit attribute if not found
                if isinstance(entry, tuple):
                    _, attr_name = entry
                    logger.warning(f"Optional resource '{attr_name}' not allocated. Omitting attribute.")
                else:
                    attr_name = self._generate_attr_name(entry)
                    logger.warning(f"Optional resource '{attr_name}' not allocated. Omitting attribute.")
                # Don't set anything

        # 3) Check that ACCESSIBLE_RESOURCES is a subset of (REQUIRED + OPTIONAL).
        declared_entries = set(required) | set(optional)
        declared_attr_names = {self._entry_to_str(e) for e in declared_entries}
        accessible_attr_names = {self._entry_to_str(e) for e in accessible}
        missing = accessible_attr_names - declared_attr_names
        if missing:
            raise ValueError(
                f"{self.__class__.__name__}: ACCESSIBLE_RESOURCES must be a subset "
                f"of REQUIRED + OPTIONAL. Missing: {missing}"
            )

    def _bind_resource(
        self, entry: Union[type, Tuple[type, str]], optional: bool
    ):
        """
        Automatically derive the attribute name if `entry` is a resource class.
        If `entry` is (ResourceClass, "custom"), use "custom".
        Then fetch from the ResourceManager (KeyError if not found).
        """
        if isinstance(entry, tuple):
            resource_cls, attr_name = entry
        else:
            resource_cls = entry
            attr_name = self._generate_attr_name(resource_cls)

        resource_obj = self.resource_manager.get_resource(attr_name)
        setattr(self, attr_name, resource_obj)

    @staticmethod
    def _generate_attr_name(resource_cls: type) -> str:
        """
        Convert a Resource class into a snake_case attribute name.
        For instance, DockerResource -> "docker_resource",
        KaliEnvResource -> "kali_env", etc.
        """
        # 1) Remove trailing "Resource" if present
        name = resource_cls.__name__
        if name.endswith("Resource"):
            name = name[: -len("Resource")]  # remove the trailing "Resource"

        # 2) snake-case it
        words = re.findall(r'[A-Z][a-z]*|\d+', name)
        return '_'.join(word.lower() for word in words)

    def _entry_to_str(self, entry: Union[type, Tuple[type, str]]) -> str:
        """
        Return the attribute name used for subset-checking in ACCESSIBLE_RESOURCES.
        If we have (ResourceClass, "my_attr"), that's "my_attr".
        If we only have ResourceClass, we derive it automatically with _generate_attr_name.
        """
        if isinstance(entry, tuple):
            return entry[1]
        return self._generate_attr_name(entry)

    @abstractmethod
    def run(self, responses: List[Response]) -> Response:
        """
        Subclasses must implement how they handle input responses
        and produce a new response.
        """
        pass