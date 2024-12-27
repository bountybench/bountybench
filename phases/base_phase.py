from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from agents.base_agent import BaseAgent
from responses.response import Response
from utils.workflow_logger import workflow_logger

@dataclass
class PhaseConfig:
    phase_idx: int
    phase_name: str
    max_iterations: int
    agents: List[Tuple[str, BaseAgent]] = field(default_factory=list)
    

class BasePhase(ABC):
    """
    Minimal example of a Phase that can allocate its agents' resources
    before run_phase.
    """
    REQUIRED_AGENTS = []

    def __init__(self, phase_config: PhaseConfig, initial_response: Optional[Response] = None, resource_manager=None):
        self.phase_config = phase_config
        self.initial_response = initial_response
        self.resource_manager = resource_manager
        self._done = False
        self.phase_summary: Optional[str] = None
        self.iteration_count = 0
        self._register_agents()

    def _register_agents(self):
        required = getattr(self, "REQUIRED_AGENTS", [])
        agent_classes = [type(a) for _, a in self.phase_config.agents]
        for rcls in required:
            if not any(issubclass(acls, rcls) for acls in agent_classes):
                raise ValueError(f"Phase requires agent {rcls.__name__}, but none provided.")

    def allocate_resources(self):
        """
        1) Tells the ResourceManager to allocate resources for this phase.
        2) Instructs each agent to bind them strictly, raising KeyError if missing.
        """
        if not self.resource_manager:
            raise RuntimeError("No resource_manager set in phase.")

        phase_name = self.phase_config.phase_name
        self.resource_manager.allocate_resources_for_phase(phase_name)

        # Now each agent can do 'bind_resources_strict'
        for _, agent in self.phase_config.agents:
            agent.register_resources()

    def run_phase(self) -> Tuple[Optional[Response], bool]:
        last_output = self.initial_response
        success_flag = False

        with workflow_logger.phase(self) as phase_ctx:
            for iteration_num in range(1, self.phase_config.max_iterations + 1):
                if self._done:
                    break

                agent_name, agent_instance = self._get_agent(iteration_num)
                self.iteration_count += 1

                with phase_ctx.iteration(iteration_num, agent_name, last_output) as iteration_ctx:
                    iteration_output, iteration_done = self.run_one_iteration(
                        agent_instance=agent_instance,
                        previous_output=last_output,
                        iteration_num=iteration_num
                    )
                    iteration_ctx.set_output(iteration_output)

                if iteration_done:
                    success_flag = True
                    self._done = True
                    last_output = iteration_output
                    break

                last_output = iteration_output

        if not self.phase_summary:
            self._set_phase_summary("completed_max_phase_iterations")
        return last_output, success_flag

    @abstractmethod
    def run_one_iteration(
        self, agent_instance: Any, previous_output: Optional[Response], iteration_num: int
    ) -> Tuple[Response, bool]:
        pass

    def _get_agent(self, iteration_num: int) -> Tuple[str, Any]:
        # simple round-robin
        idx = (iteration_num - 1) % len(self.phase_config.agents)
        return self.phase_config.agents[idx]

    def _set_phase_summary(self, summary: str):
        self.phase_summary = summary