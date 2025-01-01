from typing import Dict, Iterable, List, Optional, Set, Tuple, Type
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource, BaseResourceConfig
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class ResourceManager:
    """
    ResourceManager is responsible for managing the lifecycle of resources across multiple phases of a workflow.
    Handles:
    1. Registration and Scheduling: Resources are registered and their usage across phases is scheduled.
    2. Initialization and Deallocation: Resources are initialized when needed and deallocated when no longer required.
    """

    def __init__(self):
        # resource_id -> resource: Stores initialized resource objects.
        self._resources: Dict[str, BaseResource] = {}
        
        #The below data structures use resource_id because resource object may not be initialized yet
        # Maps resource_id -> (ResourceClass, ResourceConfig)
        self._resource_registration: Dict[str, Tuple[Type[BaseResource], Optional[BaseResourceConfig]]] = {}
        # phase_int -> set(resource_ids). Tracks which resources used by each phase.
        self._phase_resources: Dict[int, Set[str]] = {}
        # resource_id -> (init_phase, term_phase)
        self._resource_lifecycle: Dict[str, Tuple[int, int]] = {}  

    @property
    def resources(self):
        return self._resources
    
    def register_resource(self, resource_id: str, resource_class: Type[BaseResource], resource_config: Optional[BaseResourceConfig] = None):
        """Register a resource with its class and configuration."""
        self._resource_registration[resource_id] = (resource_class, resource_config)
        logger.debug(f"Registered resource '{resource_id}' with {getattr(resource_class, '__name__', str(resource_class))}.")

    def compute_schedule(self, phases: List[Type[BasePhase]]):
        """
        Compute the resource usage schedule across all phases.
        This method populates the phase_resources and resource_lifecycle dictionaries.
        """
        resource_phases = {}

        for i, phase_cls in enumerate(phases):
            phase_resources = phase_cls.get_required_resources()
            self._phase_resources[i] = phase_resources
            for resource_id in phase_resources:
                if resource_id not in resource_phases:
                    resource_phases[resource_id] = set()
                resource_phases[resource_id].add(i)

        for resource_id, phases in resource_phases.items():
            init_phase = min(phases)
            term_phase = max(phases)
            self._resource_lifecycle[resource_id] = (init_phase, term_phase)

    def initialize_phase_resources(self, phase_index: int, resource_ids: Iterable[str]):
            print(f"Debugging: Entering initialize_phase_resources for phase {phase_index}")
            print(f"Debugging: Registered resources: {self._resource_registration.keys()}")
            print(f"Debugging: Phase resources: {resource_ids}")
            
            self._phase_resources[phase_index] = set(resource_ids)
            
            for resource_id in resource_ids:
                if resource_id in self._resources:
                    print(f"Debugging: Resource '{resource_id}' already initialized. Skipping.")
                    continue

                print(f"Debugging: Attempting to initialize resource '{resource_id}'")
                if resource_id not in self._resource_registration:
                    print(f"Debugging: Resource '{resource_id}' not registered. Skipping.")
                    continue
                
                resource_class, resource_config = self._resource_registration[resource_id]
                try:
                    resource = resource_class(resource_id, resource_config)
                    self._resources[resource_id] = resource
                    print(f"Debugging: Successfully initialized resource '{resource_id}'")
                except Exception as e:
                    print(f"Debugging: Failed to initialize resource '{resource_id}': {str(e)}")
                    raise
            print(f"Debugging: Exiting initialize_phase_resources for phase {phase_index}")


    def deallocate_phase_resources(self, phase_index: int):
        """Deallocate resources that are no longer needed after a specific phase."""
        for resource_id in self._phase_resources[phase_index]:
            _, term_phase = self._resource_lifecycle[resource_id]
            if phase_index == term_phase and resource_id in self._resources:
                resource = self._resources[resource_id]
                try:
                    resource.stop()
                    del self._resources[resource_id]
                    logger.info(f"Deallocated resource '{resource_id}'")
                except Exception as e:
                    logger.error(f"Failed to deallocate resource '{resource_id}': {str(e)}")

    def get_resource(self, resource_id: str) -> BaseResource:
        """Retrieve an initialized resource by its ID."""
        if resource_id not in self._resources:
            raise KeyError(f"Resource '{resource_id}' not initialized")
        return self._resources[resource_id]
    
    def get_phase_resources(self, phase_index: int) -> Dict[str, BaseResource]:
        """Retrieve resources used by a phase by its ID."""
        return {resource_id: self.get_resource(resource_id) 
                for resource_id in self._phase_resources.get(phase_index, [])}

    def get_registered_resource_classes(self) -> List[Type[BaseResource]]:
        """
        Returns a list of all registered resource classes.
        """
        return [resource_class for resource_class, _ in self._resource_registration.values()]
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for resource in self._resources.values():
            resource.stop()
        self._resources.clear()