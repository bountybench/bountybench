from typing import Dict, List, Set, Type, Optional, Any, Union, Tuple
from dataclasses import dataclass
from phases.base_phase import PhaseConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.resource_dict import resource_dict
from utils.logger import get_main_logger

"""
Shouldn't a Resource contain a ResourceConfig? That is, a Resource is instantiated based on parameters?

"""



logger = get_main_logger(__name__)

class ResourceManager:
    """
    Manages the lifecycle of resources across multiple phases.
    Each resource is identified by a unique `resource_id`.
    """

    def __init__(self, resource_dict=None):
        """
        Args:
            resource_dict: Optional shared dictionary for resources, if used in your code.
        """
        self.resource_dict = resource_dict

        # Maps resource_id -> (ResourceClass, ResourceConfig)
        self._registrations: Dict[str, Tuple[Type[BaseResource], Optional[BaseResourceConfig]]] = {}

        # Maps resource_id -> active resource instance
        self._instances: Dict[str, BaseResource] = {}

        # Maps phase_name -> set of resource_ids needed by that phase
        self._phase_resources: Dict[str, Set[str]] = {}

        # Tracks currently active phases
        self._active_phases: Set[str] = set()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_resource(
        self,
        resource_id: str,
        resource_class: Type[BaseResource],
        resource_config: Optional[BaseResourceConfig] = None
    ):
        """
        Register a resource under `resource_id`, specifying its class and optional config.
        No actual instance is created yet.
        """
        self._registrations[resource_id] = (resource_class, resource_config)
        logger.debug(f"Registered resource '{resource_id}' with {resource_class.__name__}.")

    def register_phase(self, phase_config: PhaseConfig):
        """
        Gathers resource IDs from the agents in this phase’s config.
        For example, an agent might define REQUIRED_RESOURCES as a list of resource IDs or (class, "some_id") tuples.
        """
        phase_name = phase_config.phase_name
        resource_ids_needed = set()

        for agent_name, agent_instance in phase_config.agents:
            required = getattr(agent_instance, "REQUIRED_RESOURCES", [])
            optional = getattr(agent_instance, "OPTIONAL_RESOURCES", [])
            all_needed = list(required) + list(optional)

            for entry in all_needed:
                # If agent uses something like `REQUIRED_RESOURCES = ["kali_env"]`
                if isinstance(entry, str):
                    resource_ids_needed.add(entry)
                # If agent uses tuples like `(SetupResource, "task_server")`
                elif isinstance(entry, tuple):
                    # e.g. (resource_class, "task_server")
                    _, rid = entry
                    resource_ids_needed.add(rid)

        self._phase_resources[phase_name] = resource_ids_needed
        logger.debug(f"Phase '{phase_name}' needs resource IDs: {resource_ids_needed}")

    # ------------------------------------------------------------------
    # Allocation / Release
    # ------------------------------------------------------------------

    def allocate_resources_for_phase(self, phase_name: str):
        """
        Allocate resources needed by this phase, creating them if not already active.
        """
        if phase_name not in self._phase_resources:
            raise ValueError(f"Phase '{phase_name}' not registered with ResourceManager.")

        logger.info(f"Allocating resources for phase '{phase_name}'.")
        self._active_phases.add(phase_name)
        needed_ids = self._phase_resources[phase_name]

        for rid in needed_ids:
            if rid not in self._instances:
                self._create_instance(rid)

    def release_resources_for_phase(self, phase_name: str):
        """
        Release resources used exclusively by this phase, if no other active phase needs them.
        """
        if phase_name not in self._phase_resources:
            raise ValueError(f"Phase '{phase_name}' not registered with ResourceManager.")

        logger.info(f"Releasing resources for phase '{phase_name}'.")
        self._active_phases.discard(phase_name)

        needed_ids = self._phase_resources[phase_name]
        for rid in needed_ids:
            if rid in self._instances and not self._is_still_needed(rid):
                self._stop_and_remove(rid)

    def stop_all_resources(self):
        """Stop every active resource, e.g. at workflow end."""
        logger.info("Stopping all allocated resources.")
        for rid in list(self._instances.keys()):
            self._stop_and_remove(rid)
        self._active_phases.clear()

    # ------------------------------------------------------------------
    # Public Access
    # ------------------------------------------------------------------

    def get_resource(self, resource_id: str) -> BaseResource:
        """
        Retrieve an active resource instance by its ID.
        If not found, raise KeyError.
        """
        if resource_id in self._instances:
            return self._instances[resource_id]

        # Optional: check resource_dict if you store them there
        if self.resource_dict and resource_id in self.resource_dict:
            return self.resource_dict[resource_id]

        raise KeyError(f"Resource '{resource_id}' not allocated or registered.")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _create_instance(self, resource_id: str):
        """Instantiate a resource from its registration info, store in _instances."""
        if resource_id not in self._registrations:
            logger.warning(f"No resource registration for '{resource_id}'.")
            return

        resource_class, resource_config = self._registrations[resource_id]
        logger.info(f"Creating instance of resource '{resource_id}' ({resource_class.__name__}).")

        instance = resource_class(resource_id=resource_id, resource_config=resource_config)
        self._instances[resource_id] = instance

        if self.resource_dict is not None:
            self.resource_dict[resource_id] = instance

    def _is_still_needed(self, resource_id: str) -> bool:
        """Check if any other active phase still needs this resource ID."""
        for phase in self._active_phases:
            if resource_id in self._phase_resources[phase]:
                return True
        return False

    def _stop_and_remove(self, resource_id: str):
        """Stop the resource, remove it from manager references, and optionally from resource_dict."""
        instance = self._instances.get(resource_id)
        if instance:
            logger.info(f"Stopping resource '{resource_id}'.")
            try:
                instance.stop()
            except Exception as e:
                logger.error(f"Error stopping resource '{resource_id}': {e}")
        self._instances.pop(resource_id, None)

        if self.resource_dict and resource_id in self.resource_dict:
            del self.resource_dict[resource_id]