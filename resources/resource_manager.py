from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple, Type, TYPE_CHECKING

from resources.base_resource import BaseResource, BaseResourceConfig
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.model_resource.model_resource import ModelResource, ModelResourceConfig
from resources.resource_dict import resource_dict
from utils.logger import get_main_logger

if TYPE_CHECKING:
    from phases.base_phase import BasePhase

logger = get_main_logger(__name__)


class ResourceManager:
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self._resources = resource_dict

        if workflow_id not in self._resources.id_to_resource:
            self._resources.id_to_resource[workflow_id] = {}
            self._resources.resource_type_to_resources[workflow_id] = defaultdict(list)

        self._resource_registration: Dict[
            str, Tuple[Type[BaseResource], Optional[BaseResourceConfig]]
        ] = {}
        self._phase_resources: Dict[int, Set[str]] = {}
        self._resource_lifecycle: Dict[str, Tuple[int, int]] = {}

    @property
    def resources(self):
        return self._resources

    def register_resource(
        self,
        resource_id: str,
        resource_class: Type[BaseResource],
        resource_config: Optional[BaseResourceConfig] = None,
    ):
        self._resource_registration[resource_id] = (resource_class, resource_config)
        logger.debug(
            f"Registered resource '{resource_id}' with {getattr(resource_class, '__name__', str(resource_class))}."
        )

    def update_model(self, new_model_name: str):
        if "model" in self._resource_registration:
            resource_class, resource_config = ModelResource, ModelResourceConfig.create(
                model=new_model_name
            )
            self._resource_registration["model"] = (resource_class, resource_config)
            resource = resource_class("model", resource_config)
            self._resources.set(self.workflow_id, "model", resource)
            logger.info(f"New model specifics: {resource}")
    
    def update_mock_model(self, use_mock_model: bool):
        """
        Updates the `use_mock_model` setting for the ModelResource.
        """
        if "model" in self._resource_registration:
            resource_class, resource_config = ModelResource, ModelResourceConfig.create(
                model=self._resource_registration["model"][1].model, 
                use_mock_model=use_mock_model 
            )
            self._resource_registration["model"] = (resource_class, resource_config)

            # Create and set the updated resource
            resource = resource_class("model", resource_config)
            self._resources.set(self.workflow_id, "model", resource)

            logger.info(f"Updated ModelResource to use_mock_model={use_mock_model}")

    def compute_schedule(self, phases: List["BasePhase"]):
        """
        Compute the resource usage schedule across all phases.
        This method populates the phase_resources and resource_lifecycle dictionaries.
        """
        resource_phases = {}

        for i, phase in enumerate(phases):
            phase_resources = phase.define_resources()
            self._phase_resources[i] = set(
                [resource.key(self.workflow_id) for (resource, _) in phase_resources]
            )
            for resource, resource_config in phase_resources:
                resource_id = resource.key(self.workflow_id)
                resource_class = resource.get_class()

                if not self.is_resource_equivalent(
                    resource_id, resource_class, resource_config
                ):
                    self.register_resource(resource_id, resource_class, resource_config)
                if resource_id not in resource_phases:
                    resource_phases[resource_id] = set()
                resource_phases[resource_id].add(i)

        for resource_id, phases in resource_phases.items():
            init_phase = min(phases)
            term_phase = max(phases)
            self._resource_lifecycle[resource_id] = (init_phase, term_phase)

        logger.debug(f"Computed resource schedule: {self._resource_lifecycle}")

    def is_resource_equivalent(
        self,
        resource_id: str,
        resource_class: Type[BaseResource],
        resource_config: Optional[BaseResourceConfig],
    ) -> bool:
        if resource_id not in self._resource_registration:
            return False
        registered_class, registered_config = self._resource_registration[resource_id]
        return registered_class == resource_class and (
            registered_config == resource_config
            or (registered_config is None and resource_config is None)
        )

    def initialize_phase_resources(self, phase_index: int, resource_ids: Iterable[str]):
        """Initialize resources for a phase and update lifecycle information."""
        logger.debug(f"Entering initialize_phase_resources for phase {phase_index}")

        resource_id_set = set(resource_ids)
        self._phase_resources[phase_index] = resource_id_set

        # Update lifecycle information
        for resource_id in resource_id_set:
            if resource_id not in self._resource_lifecycle:
                self._resource_lifecycle[resource_id] = (phase_index, phase_index)
            else:
                init_phase, term_phase = self._resource_lifecycle[resource_id]
                self._resource_lifecycle[resource_id] = (
                    init_phase,
                    max(phase_index, term_phase),
                )

        # Separate InitFilesResource from other resources
        init_files_resource_id = next(
            (
                rid
                for rid in resource_id_set
                if self._resource_registration.get(rid)
                and issubclass(self._resource_registration[rid][0], InitFilesResource)
            ),
            None,
        )

        kali_resource_id = next(
            (
                rid
                for rid in resource_id_set
                if self._resource_registration.get(rid)
                and issubclass(self._resource_registration[rid][0], KaliEnvResource)
            ),
            None,
        )

        # other_resource_ids = resource_id_set - {init_files_resource_id} if init_files_resource_id else resource_id_set

        other_resource_ids = resource_id_set - {
            init_files_resource_id,
            kali_resource_id,
        }

        # Initialize InitFilesResource first if it exists
        if init_files_resource_id:
            self._initialize_single_resource(init_files_resource_id, phase_index)

        # Initialize other resources
        for resource_id in other_resource_ids:
            self._initialize_single_resource(resource_id, phase_index)

        if kali_resource_id:
            self._initialize_single_resource(kali_resource_id, phase_index)

        logger.debug(f"Resource lifecycle state: {self._resource_lifecycle}")
        logger.debug(f"Exiting initialize_phase_resources for phase {phase_index}")

    def _initialize_single_resource(self, resource_id: str, phase_index: int):
        """Initialize a single resource."""
        if resource_id in self._resources.id_to_resource.get(self.workflow_id, {}):
            logger.info(f"Resource '{resource_id}' already initialized. Skipping.")
            return

        logger.info(f"Attempting to initialize resource '{resource_id}'")
        if resource_id not in self._resource_registration:
            logger.info(f"Resource '{resource_id}' not registered. Skipping.")
            return

        resource_class, resource_config = self._resource_registration[resource_id]
        logger.info(
            f"resource_class, resource_config: {resource_class}, {resource_config}"
        )
        try:
            resource = resource_class(resource_id, resource_config)
            self._resources.set(self.workflow_id, resource_id, resource)
            logger.info(f"Successfully initialized resource '{resource_id}'")
        except Exception as e:
            logger.error(f"Failed to initialize resource '{resource_id}': {str(e)}")
            raise

    def deallocate_phase_resources(self, phase_index: int):
        """Deallocate resources that are no longer needed after a phase."""
        logger.debug(f"Deallocating resources for phase {phase_index}")
        logger.debug(
            f"Current phase resources: {self._phase_resources.get(phase_index, set())}"
        )
        logger.debug(f"Current lifecycle state: {self._resource_lifecycle}")

        if phase_index not in self._phase_resources:
            logger.warning(f"No resources registered for phase {phase_index}")
            return

        resources_to_deallocate = []
        init_files_resource = None

        for resource_id in self._phase_resources[phase_index]:
            if resource_id not in self._resource_lifecycle:
                logger.warning(f"No lifecycle information for resource '{resource_id}'")
                continue

            _, term_phase = self._resource_lifecycle[resource_id]
            if (
                phase_index == term_phase
                and resource_id
                in self._resources.id_to_resource.get(self.workflow_id, {})
            ):
                resource = self._resources.get(self.workflow_id, resource_id)
                if isinstance(resource, InitFilesResource):
                    init_files_resource = (resource_id, resource)
                else:
                    resources_to_deallocate.append((resource_id, resource))

        # Deallocate non-InitFilesResource resources
        for resource_id, resource in resources_to_deallocate:
            try:
                logger.debug(f"Stopping resource '{resource_id}'")
                resource.stop()
                self._resources.delete_items(self.workflow_id, resource_id)
                logger.info(f"Deallocated resource '{resource_id}'")
            except Exception as e:
                logger.error(f"Failed to deallocate resource '{resource_id}': {str(e)}")
                raise

        # Deallocate InitFilesResource last, if it exists
        if init_files_resource:
            resource_id, resource = init_files_resource
            try:
                logger.debug(f"Stopping InitFilesResource '{resource_id}'")
                resource.stop()
                self._resources.delete_items(self.workflow_id, resource_id)
                logger.info(f"Deallocated InitFilesResource '{resource_id}'")
            except Exception as e:
                logger.error(
                    f"Failed to deallocate InitFilesResource '{resource_id}': {str(e)}"
                )
                raise

        logger.info(f"Completed resource deallocation for phase {phase_index}")

    def get_resource(self, resource_id: str) -> BaseResource:
        """Retrieve an initialized resource by its ID."""
        if resource_id not in self._resources.id_to_resource.get(self.workflow_id, {}):
            raise KeyError(f"Resource '{resource_id}' not initialized")
        return self._resources.get(self.workflow_id, resource_id)

    def get_phase_resources(self, phase_index: int) -> Dict[str, BaseResource]:
        """Retrieve resources used by a phase by its ID."""
        return {
            resource_id: self.get_resource(resource_id)
            for resource_id in self._phase_resources.get(phase_index, [])
        }

    def get_registered_resource_classes(self) -> List[Type[BaseResource]]:
        """
        Returns a list of all registered resource classes.
        """
        return [
            resource_class for resource_class, _ in self._resource_registration.values()
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for resource in self._resources.id_to_resource.get(
            self.workflow_id, {}
        ).values():
            resource.stop()
        if self.workflow_id in self._resources.id_to_resource:
            del self._resources.id_to_resource[self.workflow_id]
        if self.workflow_id in self._resources.resource_type_to_resources:
            del self._resources.resource_type_to_resources[self.workflow_id]

    def deallocate_all_resources(self):
        """Deallocate all resources for the current workflow."""
        for resource in list(
            self._resources.id_to_resource.get(self.workflow_id, {}).values()
        ):
            resource.stop()
        if self.workflow_id in self._resources.id_to_resource:
            del self._resources.id_to_resource[self.workflow_id]
        if self.workflow_id in self._resources.resource_type_to_resources:
            del self._resources.resource_type_to_resources[self.workflow_id]
        self._resource_registration.clear()
        self._phase_resources.clear()
        self._resource_lifecycle.clear()

    def get_resources(self):
        return self._resources.id_to_resource[self.workflow_id]
