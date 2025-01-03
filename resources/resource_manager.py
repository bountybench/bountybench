from typing import Dict, Iterable, List, Optional, Set, Tuple, Type
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource, BaseResourceConfig
from utils.logger import get_main_logger
from utils.workflow_logger import workflow_logger

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
        """Initialize resources for a phase and update lifecycle information."""
        logger.debug(f"Entering initialize_phase_resources for phase {phase_index}")
        logger.debug(f"Registered resources: {self._resource_registration.keys()}")
        logger.debug(f"Phase resources: {resource_ids}")
        
        # Convert resource_ids to set and store in phase_resources
        resource_id_set = set(resource_ids)
        self._phase_resources[phase_index] = resource_id_set
        
        # Update lifecycle information for each resource
        for resource_id in resource_id_set:
            if resource_id not in self._resource_lifecycle:
                # If not in lifecycle dict, this is the first phase using it
                self._resource_lifecycle[resource_id] = (phase_index, phase_index)
            else:
                # Update term_phase if this phase is later
                init_phase, _ = self._resource_lifecycle[resource_id]
                self._resource_lifecycle[resource_id] = (init_phase, max(phase_index, self._resource_lifecycle[resource_id][1]))
        
        # Initialize resources that aren't already initialized
        for resource_id in resource_id_set:
            if resource_id in self._resources:
                logger.debug(f"Resource '{resource_id}' already initialized. Skipping.")
                continue

            logger.debug(f"Attempting to initialize resource '{resource_id}'")
            if resource_id not in self._resource_registration:
                logger.debug(f"Resource '{resource_id}' not registered. Skipping.")
                continue
            
            # Create and initialize the resource
            resource_class, resource_config = self._resource_registration[resource_id]
            try:
                resource = resource_class(resource_id, resource_config)
                if hasattr(resource, "role"):
                    workflow_logger.add_resource(f"{resource.__class__.__name__}: {resource.role}", resource)
                else:
                    workflow_logger.add_resource(f"{resource.__class__.__name__}: {resource.resource_id}", resource)
                
                self._resources[resource_id] = resource
                logger.debug(f"Successfully initialized resource '{resource_id}'")
            except Exception as e:
                logger.debug(f"Failed to initialize resource '{resource_id}': {str(e)}")
                raise
                
        logger.debug(f"Resource lifecycle state: {self._resource_lifecycle}")
        logger.debug(f"Exiting initialize_phase_resources for phase {phase_index}")

    def deallocate_phase_resources(self, phase_index: int):
        """Deallocate resources that are no longer needed after a phase."""
        logger.debug(f"Deallocating resources for phase {phase_index}")
        logger.debug(f"Current phase resources: {self._phase_resources.get(phase_index, set())}")
        logger.debug(f"Current lifecycle state: {self._resource_lifecycle}")
        
        if phase_index not in self._phase_resources:
            print(f"Warning: No resources registered for phase {phase_index}")
            return
            
        for resource_id in self._phase_resources[phase_index]:
            # Skip if resource not in lifecycle dict (shouldn't happen with fixes)
            if resource_id not in self._resource_lifecycle:
                print(f"Warning: No lifecycle information for resource '{resource_id}'")
                continue
                
            _, term_phase = self._resource_lifecycle[resource_id]
            if phase_index == term_phase and resource_id in self._resources:
                resource = self._resources[resource_id]
                try:
                    logger.debug(f"Stopping resource '{resource_id}'")
                    resource.stop()
                    del self._resources[resource_id]
                    logger.info(f"Deallocated resource '{resource_id}'")
                except Exception as e:
                    logger.error(f"Failed to deallocate resource '{resource_id}': {str(e)}")
                    raise
                    
        logger.debug(f"Completed resource deallocation for phase {phase_index}")

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