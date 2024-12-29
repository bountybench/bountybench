from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set, Tuple, Union

from agents.base_agent import BaseAgent
from responses.response import Response
from utils.workflow_logger import workflow_logger

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

@dataclass
class PhaseConfig:
    phase_idx: int
    phase_name: str
    max_iterations: int
    agents: List[Tuple[str, BaseAgent]] = field(default_factory=list)
    interactive: bool = False
    
class BasePhase(ABC):
    """
    Minimal example of a Phase that can allocate its agents' resources
    before run_phase.
    """

    REQUIRED_AGENTS: List[Union[str, Tuple[BaseAgent, str]]] = []

    def __init__(self, phase_config: PhaseConfig, initial_response: Optional[Response] = None, 
        resource_manager=None, workflow=None, ):
        self.phase_config = phase_config
        self.initial_response = initial_response
        self.resource_manager = resource_manager
        self.workflow = workflow 
        self._done = False
        self.phase_summary: Optional[str] = None
        self.iteration_count = 0  # Will increment up to max_iterations
        self.current_agent_index = 0

        # Check that the agents in config match what we require (if any)
        self._register_agents()

    @classmethod
    def get_required_resources(cls) -> Set[str]:
        resources = set()
        for agent_cls in cls.REQUIRED_AGENTS:
            resources.update(agent_cls.get_required_resources())
        return resources
    
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

    async def run_phase(self) -> Tuple[Optional[Response], bool]:
        print(f"Running phase with interactive {self.phase_config.interactive}")
        last_output = self.initial_response
        success_flag = False
        
        # 1) Start phase context
        with workflow_logger.phase(self) as phase_ctx:
            for iteration_num in range(1, self.phase_config.max_iterations + 1):
                if self._done:
                    break

                if self.phase_config.interactive:
                    if hasattr(self.workflow, 'next_iteration_event'):
                        logger.info("Waiting for 'next' signal ...")
                        self.workflow.next_iteration_event.clear()
                        await self.workflow.next_iteration_event.wait()
                    else:
                        logger.warning("Interactive mode is set, but workflow doesn't have next_iteration_event")

                        
                agent_name, agent_instance = self._get_agent()

                # 2) Start iteration context in the logger
                with phase_ctx.iteration(iteration_num, agent_name, last_output) as iteration_ctx:
                    print("Let's run one iteration")
                    iteration_output, iteration_done = await self.run_one_iteration(
                        agent_instance=agent_instance,
                        previous_output=last_output,
                        iteration_num=iteration_num
                    )
                    iteration_ctx.set_output(iteration_output)
                    logger.info(f"Iteration output:\n")
                    logger.info(iteration_output.response)
                if iteration_done:
                    success_flag = True
                    self._done = True
                    last_output = iteration_output
                    break

                last_output = iteration_output

                # Increment the iteration count
                self.iteration_count += 1
                self.current_agent_index += 1

        if not self.phase_summary:
            self._set_phase_summary("completed_max_phase_iterations")
        return last_output, success_flag
    
    def _get_agent(self) -> Tuple[str, BaseAgent]:
        agent_index = (self.current_agent_index) % len(self.phase_config.agents)
        agent_name, agent_instance = self.phase_config.agents[agent_index]
        return agent_name, agent_instance

    def _set_phase_summary(self, summary: str):
        """Allows a subclass to record a short message describing the phase outcome.
        Example: self.set_phase_summary("exploit_success")
        Or sets as completed_max_phase_iterations if no summary set"""
        self.phase_summary = summary

    @abstractmethod
    async def run_one_iteration(
        self, agent_instance: Any, previous_output: Optional[Response], iteration_num: int
    ) -> Tuple[Response, bool]:
        pass

    def _set_phase_summary(self, summary: str):
        self.phase_summary = summary