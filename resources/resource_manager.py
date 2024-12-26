from typing import Dict, List, Set, Type
from phases.base_phase import PhaseConfig
from resources.base_resource import BaseResource

class ResourceManager:
    def __init__(self):
        self.resources: Dict[str, BaseResource] = {}
        self.phase_resources: Dict[str, Set[str]] = {}
        self.allocated_resources: Set[str] = set()
        self.active_phases: Set[str] = set()

    def register_phase(self, phase_config: PhaseConfig):
        phase_name = phase_config.phase_name
        self.phase_resources[phase_name] = set()
        for _, agent in phase_config.agents:
            for resource_list in [agent.REQUIRED_RESOURCES, agent.OPTIONAL_RESOURCES, agent.ACCESSIBLE_RESOURCES]:
                for resource in resource_list:
                    resource_name = resource[0].__name__ if isinstance(resource, tuple) else resource.__name__
                    self.phase_resources[phase_name].add(resource_name)

    def allocate_resources(self, phase_name: str):
        if phase_name not in self.phase_resources:
            raise ValueError(f"Phase {phase_name} not registered")
        self.active_phases.add(phase_name)
        for resource_name in self.phase_resources[phase_name]:
            if resource_name not in self.allocated_resources:
                self.allocated_resources.add(resource_name)

    def release_resources(self, phase_name: str):
        if phase_name not in self.phase_resources:
            raise ValueError(f"Phase {phase_name} not registered")
        self.active_phases.remove(phase_name)
        resources_to_release = set(self.allocated_resources)
        for active_phase in self.active_phases:
            resources_to_release -= self.phase_resources[active_phase]
        self.allocated_resources -= resources_to_release

    def _is_resource_needed_by_other_phases(self, resource_name: str, current_phase: str) -> bool:
        return any(resource_name in resources for phase, resources in self.phase_resources.items() if phase != current_phase and phase in self.active_phases)

    def add_resource(self, resource: BaseResource):
        self.resources[resource.__class__.__name__] = resource

    def get_resource(self, resource_name: str) -> BaseResource:
        return self.resources[resource_name]

    def get_all_resources_by_phases(self) -> Dict[str, Set[str]]:
        return self.phase_resources.copy()