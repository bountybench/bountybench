from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from agents.base_agent import BaseAgent
from responses.response import Response
from utils.workflow_logger import WorkflowLogger

@dataclass
class PhaseConfig:
    phase_number: int
    phase_name: str
    max_iterations: int
    agents: List[Tuple[str, BaseAgent]] = field(default_factory=list)
    
class BasePhase(ABC):
    """
    A base class that:
      - Opens and closes a workflow "phase" in the logger.
      - Iterates a certain number of times.
      - For each iteration, logs the agent name, input, and output automatically.
        
    PhaseConfig defines:
      - phase_number (int)
      - phase_name (str)
      - max_iterations (int)
      - agents (List[BaseAgent])
    
    Subclasses only need to implement how to run one iteration with a given agent. 
    Subclass can define expected (required) agents, BasePhase automatically ensures compliance with expected list.
    """

    def __init__(
        self,
        workflow_logger: WorkflowLogger,
        phase_config: PhaseConfig,
        initial_response: Optional[Response] = None
    ):
        """
        Args:
            workflow_logger (WorkflowLogger): The shared logger instance.
            phase_config (PhaseConfig): Contains phase_number, phase_name, max_iterations, agents list.
            initial_response (Optional[Response]): Response context from previous phase.
        """
        self.workflow_logger = workflow_logger
        self.phase_config = phase_config
        self.initial_response = initial_response

        self._done = False  # Set to True when phase logic completes early
        self._iteration_count = 0  # Will increment up to max_iterations

        # TODO: Log agent for each phase?

        # Check that the agents in config match what we require (if any)
        self._register_agents()

    def _register_agents(self):
        """
        Checks that all REQUIRED_AGENTS are present among the agents in `phase_config`.
        For example, if REQUIRED_AGENTS = [ExecutorAgent, ExploitAgent],
        then among the config.agents, we must have at least one instance of ExecutorAgent,
        and at least one instance of ExploitAgent.

        If anything is missing, raises ValueError/TypeError, etc.
        """
        if not self.REQUIRED_AGENTS:
            return  # No special requirement

        # For each required agent type, ensure at least one config.agents matches
        agent_classes_in_config = [type(agent_instance) for (_name, agent_instance) in self.phase_config.agents]

        for required_cls in self.REQUIRED_AGENTS:
            # Check if any agent in config is an instance of required_cls
            if not any(isinstance(agent_instance, required_cls) for (_n, agent_instance) in self.phase_config.agents):
                raise ValueError(
                    f"{self.__class__.__name__} requires an agent of type {required_cls.__name__}, "
                    f"but none was found in phase_config.agents: {agent_classes_in_config}"
                )

    def run_phase(self) -> Tuple[Optional[Response], bool]:
        """
        Top-level method to run entire phase:
          1) Start the phase in the logger.
          2) Iterate up to config.max_iterations.
          3) Cycle through the list of agents.
          4) Subclass implements run_one_iteration(agent, previous_output).
          5) If run_one_iteration returns (response, True), we stop early (success).

        Returns:
            (last_output_response, success_flag)
        """
        last_output = self.initial_response
        success_flag = False

        # 1) Start phase context
        with self.workflow_logger.phase(self.config.phase_number, self.config.phase_name) as phase_ctx:
            for iteration_num in range(1, self.config.max_iterations + 1):
                if self._done:
                    break

                agent_name, agent_instance = self._get_agent(iteration_num)

                # 2) Start iteration context in the logger
                with phase_ctx.iteration(iteration_num, agent_name, last_output) as iteration_ctx:
                    # 3) Subclass logic for one iteration
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

        return last_output, success_flag

    def _get_agent(self, iteration_num: int) -> Tuple[str, BaseAgent]:
        # Pick the next agent from config.agents (cycling if >1 agent)
        agent_index = (iteration_num - 1) % len(self.config.agents)
        agent_name, agent_instance = self.config.agents[agent_index]
        return agent_name, agent_instance

    @abstractmethod
    def run_one_iteration(
        self,
        previous_output: Optional[Response],
        iteration_num: int
    ) -> Tuple[Response, bool]:
        """
        The subclass implements the actual logic of one iteration:
          - Possibly call an agent with the previous output as input.
          - Produce a new output (Response).
          - Return (new_output, done_flag).

        done_flag = True means we can stop early (e.g. exploit success).
        """
        pass
