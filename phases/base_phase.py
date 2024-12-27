from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from agents.base_agent import BaseAgent
from responses.base_response import BaseResponse
from responses.edit_response import EditResponse
from responses.response import Response
from utils.workflow_logger import workflow_logger

@dataclass
class PhaseConfig:
    phase_idx: int
    phase_name: str
    max_iterations: int
    agents: List[Tuple[str, BaseAgent]] = field(default_factory=list)
    interactive: bool = False
    
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
        phase_config: PhaseConfig,
        initial_response: Optional[Response] = None
    ):
        """
        Args:
            phase_config (PhaseConfig): Contains phase_number, phase_name, max_iterations, agents list.
            initial_response (Optional[Response]): Response context from previous phase.
        """
        self.phase_config = phase_config
        self.initial_response = initial_response

        self._done = False  # Set to True when phase logic completes early
        self.phase_summary: Optional[str] = None
        self.iteration_count = 0  # Will increment up to max_iterations
        self.current_agent_index = 0

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
        required_agents = getattr(self, "REQUIRED_AGENTS", [])
        if not required_agents:
            return  # No special requirement

        # For each required agent type, ensure at least one config.agents matches
        agent_classes_in_config = [type(agent_instance) for (_name, agent_instance) in self.phase_config.agents]

        for required_cls in required_agents:
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

        skip_interactive = 0
        
        # 1) Start phase context
        with workflow_logger.phase(self) as phase_ctx:
            for iteration_num in range(1, self.phase_config.max_iterations + 1):
                if self._done:
                    break

                agent_name, agent_instance = self._get_agent()

                if self.phase_config.interactive and skip_interactive <= 0:
                    skip_interactive, last_output = self._interactive_prompt(iteration_num, last_output)
                    if self._done:
                        break
                else:
                    skip_interactive -= 1


                if last_output:
                    print(f"Last output was {last_output.response}")
                else:
                    print("No last output")

                # 2) Start iteration context in the logger
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

                # Increment the iteration count
                self.iteration_count += 1
                self.current_agent_index += 1

        if not self.phase_summary:
            self._set_phase_summary("completed_max_phase_iterations")
        return last_output, success_flag

    def _interactive_prompt(self, iteration_num: int, current_response: Optional[Response]) -> Tuple[int, Optional[Response]]:
        while True:
            user_input = input(f"Iteration {iteration_num}.\n"
                               f"To step through run: Press Enter to continue, 'q' to quit, or 'c#' to continue # iterations.\n"
                               f"To edit run: Press 'a' to edit or add to current Response, 'E' to edit initial_prompt (will reset agents but not iteration count).\n"
                               f"Input: ")

            if user_input.lower() == 'q':
                self._done = True
                return 0, current_response
            elif user_input.startswith('c'):
                try:
                    num_iterations = int(user_input[1:])
                    if num_iterations > 0:
                        return num_iterations - 1, current_response
                    else:
                        print("Please enter a positive number after 'c'.")
                except ValueError:
                    print("Invalid input. Please enter a number after 'c'.")
            elif user_input == '':
                return 0, current_response
            elif user_input.lower() == 'a':
                current_response = self._edit_response(current_response)
            elif user_input == 'e':
                # Implement 'e' option if needed
                pass
            elif user_input == 'E':
                if hasattr(self, 'initial_response') and self.initial_response:
                    new_initial_response = self._edit_response(EditResponse(self.initial_response.response))
                    self.initial_response = new_initial_response
                    
                    self.current_agent_index = 0
                    return 0, new_initial_response
                else:
                    print("Cannot edit initial prompt: workflow reference or initial prompt not available.")
            else:
                print("Invalid input. Press Enter to continue, 'q' to quit, 'c#' to continue # iterations, 'a' to edit current Response, or 'E' to edit initial prompt.")

    def _edit_response(self, response: Optional[Response]) -> EditResponse:
        if response is None:
            edit_response = EditResponse("")
        else:
            edit_response = EditResponse(response.response)

        print(f"Current response:\n{edit_response.response}\n")
        edit_input = input("Enter text to add or edit (prefix with 'edit:' to replace entire response):\n")
        
        if edit_input.startswith("edit:"):
            edit_response.edit(edit_input[5:].strip())
        else:
            edit_response.add("\n" + edit_input)
        
        print(f"Updated response:\n{edit_response.response}\n")
        return edit_response
    
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
