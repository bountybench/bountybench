from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set, Tuple, Union

from agents.base_agent import BaseAgent
from responses.base_response import BaseResponse
from responses.edit_response import EditResponse
from responses.response import Response
from utils.workflow_logger import workflow_logger

@dataclass
class PhaseConfig:
    phase_idx: int
    max_iterations: int
    agents: List[Tuple[str, BaseAgent]] = field(default_factory=list)
    interactive: bool = False
    
class BasePhase(ABC):
    """
    Minimal example of a Phase that can allocate its agents' resources
    before run_phase.
    """

    REQUIRED_AGENTS: List[Union[str, Tuple[BaseAgent, str]]] = []

    def __init__(self, phase_config: PhaseConfig, initial_response: Optional[Response] = None, resource_manager=None):
        self.phase_config = phase_config
        self.initial_response = initial_response
        self.resource_manager = resource_manager
        self._done = False
        self.phase_summary: Optional[str] = None
        self.iteration_count = 0  # Will increment up to max_iterations
        self.current_agent_index = 0

        # TODO: Log agent for each phase?

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

    def run_phase(self) -> Tuple[Optional[Response], bool]:
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
        self, agent_instance: Any, previous_output: Optional[Response], iteration_num: int
    ) -> Tuple[Response, bool]:
        pass

    def _get_agent(self, iteration_num: int) -> Tuple[str, Any]:
        # simple round-robin
        idx = (iteration_num - 1) % len(self.phase_config.agents)
        return self.phase_config.agents[idx]

    def _set_phase_summary(self, summary: str):
        self.phase_summary = summary