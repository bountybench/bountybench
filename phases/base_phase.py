from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional, Set, Tuple, Type, Union

from agents.base_agent import AgentConfig, BaseAgent
from responses.base_response import BaseResponse
from responses.edit_response import EditResponse
from responses.response import Response
from utils.logger import get_main_logger
from utils.workflow_logger import workflow_logger

logger = get_main_logger(__name__)


if TYPE_CHECKING:
    from agents.agent_manager import AgentManager  # Only import for type checking
    from workflows.base_workflow import BaseWorkflow

@dataclass
class PhaseConfig:
    max_iterations: int
    phase_name: str = "base_phase"
    agent_configs: List[Tuple[str, 'AgentConfig']] = field(default_factory=list)  # List of (agent_id, AgentConfig)
    interactive: bool = False
    phase_idx: Optional[int] = None



class BasePhase(ABC):
    AGENT_CLASSES: List[Type[BaseAgent]] = []

    def __init__(
        self,
        phase_config: PhaseConfig,
        agent_manager: 'AgentManager',
        workflow: 'BaseWorkflow',
        initial_response: Optional[BaseResponse] = None
    ):
        self.workflow = workflow
        self.phase_config = phase_config
        self.agent_manager = agent_manager
        self.agents: List[Tuple[str, BaseAgent]] = []
        self.initial_response = initial_response
        self._done = False
        self.resource_manager = agent_manager.resource_manager
        self.phase_summary: Optional[str] = None
        self.iteration_count = 0
        self.current_agent_index = 0

        phase_config.phase_name = self.name
        phase_config.agent_configs = self.get_agent_configs()
        print("THIS IS MY PHASE AGENT CONFIGS", phase_config.agent_configs)
        self._initialize_agents()

    def get_phase_resources(self):
        phase_resources = {}
        for agent_class in self.AGENT_CLASSES:
            phase_resources.update(agent_class.REQUIRED_RESOURCES)
        return phase_resources

    def _initialize_agents(self):
        """Initialize and register required agents using AgentManager."""
        for agent_id, agent_config in self.phase_config.agent_configs:
            # Find matching agent class based on config type
            agent_class = next(
                (ac for ac in self.AGENT_CLASSES if isinstance(agent_config, ac.CONFIG_CLASS)), 
                None
            )
            if not agent_class:
                continue

            agent_instance = self.agent_manager.get_or_create_agent(agent_id, agent_class, agent_config) 
            self.agents.append((agent_id, agent_instance))

        # Verify all required agents present
        required_classes = set(self.AGENT_CLASSES)
        present_classes = {type(agent) for _, agent in self.agents}
        missing = required_classes - present_classes
        if missing:
            missing_names = ', '.join(agent.__name__ for agent in missing)
            raise ValueError(f"Phase '{self.phase_config.phase_name}' requires agents: {missing_names}")
        
    def _initialize_resources(self):
        resource_configs = self.define_resources()
        for resource_id, resource_config in resource_configs.items():
            resource_class = type(resource_config).__name__.replace("Config", "")
            self.resource_manager.register_resource(resource_id, globals()[resource_class], resource_config)
        
        for _, agent in self.agents:
            agent.register_resources(self.resource_manager)

    def register_resources(self):
        """
        Register required resources with the ResourceManager.
        Should be called after resources are initialized for the phase.
        """
        print(f"Debugging: Registering resources for phase {self.phase_config.phase_idx} ({self.phase_config.phase_name})")
        for agent_id, agent in self.agents:
            print(f"Debugging: Registering resources for agent {agent_id}")
            agent.register_resources()
        print(f"Debugging: Finished registering resources for phase {self.phase_config.phase_idx}")


    @classmethod
    def get_required_resources(cls) -> Set[str]:
        resources = set()
        for agent_cls in cls.AGENT_CLASSES:
            resources.update(agent_cls.get_required_resources())
        return resources



    def _initialize_resources(self):
        resource_configs = self.define_resources()
        for resource_id, resource_config in resource_configs.items():
            resource_class = type(resource_config).__name__.replace("Config", "")
            self.resource_manager.register_resource(resource_id, globals()[resource_class], resource_config)
        
        for _, agent in self.agents:
            agent.register_resources(self.resource_manager)



    def deallocate_resources(self):
        """
        Deallocate resources after the phase is completed.
        """
        try:
            self.resource_manager.deallocate_phase_resources(self.phase_config.phase_idx)
            logger.info(f"Phase {self.phase_config.phase_idx} ({self.phase_config.phase_name}) resources deallocated.")
        except Exception as e:
            logger.error(f"Failed to deallocate resources for phase {self.phase_config.phase_idx}: {e}")
            raise

    def run_phase(self) -> Tuple[Optional[BaseResponse], bool]:
        """
        Execute the phase by running its iterations.

        Returns:
            Tuple[Optional[BaseResponse], bool]: The last response and a success flag.
        """
        print(f"Debugging: Entering run_phase for phase {self.phase_config.phase_idx} ({self.phase_config.phase_name})")

        last_output = self.initial_response
        success_flag = False

        skip_interactive = 0

        # Initialize resources before starting iterations
        self.initialize_resources()

        # 1) Start phase context
        with workflow_logger.phase(self) as phase_ctx:
            for iteration_num in range(1, self.phase_config.max_iterations + 1):
                if self._done:
                    break

                agent_id, agent_instance = self._get_current_agent()

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
                with phase_ctx.iteration(iteration_num, agent_id, last_output) as iteration_ctx:
                    response, done = self.run_one_iteration(
                        agent_instance=agent_instance,
                        previous_output=last_output,
                        iteration_num=iteration_num
                    )
                    iteration_ctx.set_output(response)

                if done:
                    success_flag = True
                    self._done = True
                    last_output = response
                    break

                last_output = response

                # Increment the iteration count
                self.iteration_count += 1
                self.current_agent_index += 1

        if not self.phase_summary:
            self._set_phase_summary("completed_max_phase_iterations")

        # Deallocate resources after completing iterations
        self.deallocate_resources()

        return last_output, success_flag

    def _interactive_prompt(self, iteration_num: int, current_response: Optional[BaseResponse]) -> Tuple[int, Optional[BaseResponse]]:
        while True:
            user_input = input(
                f"Iteration {iteration_num}.\n"
                f"To step through run: Press Enter to continue, 'q' to quit, or 'c#' to continue # iterations.\n"
                f"To edit run: Press 'a' to edit or add to current Response, 'E' to edit initial_prompt (will reset agents but not iteration count).\n"
                f"Input: "
            )

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

    def _edit_response(self, response: Optional[BaseResponse]) -> BaseResponse:
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

    def _get_current_agent(self) -> Tuple[str, BaseAgent]:
        """Retrieve the next agent in a round-robin fashion."""
        agent = self.agents[self.current_agent_index % len(self.agents)]
        self.current_agent_index += 1
        return agent

    def _set_phase_summary(self, summary: str):
        """Allows a subclass to record a short message describing the phase outcome."""
        self.phase_summary = summary

    @abstractmethod
    def get_agent_configs(self) -> List[Tuple[str, AgentConfig]]:
        """
        Provide agent configurations for the phase.

        Returns:
            List[Tuple[str, AgentConfig]]: List of (agent_id, AgentConfig) tuples.
        """
        pass


    @abstractmethod
    def get_agent_configs(self) -> List[Tuple[str, AgentConfig]]:
        pass

    
    @abstractmethod
    def define_resources(self): 
        pass

    @abstractmethod
    def run_one_iteration(
        self, agent_instance: Any, previous_output: Optional[BaseResponse], iteration_num: int
    ) -> Tuple[BaseResponse, bool]:
        """
        Run a single iteration of the phase.

        Args:
            agent_instance (BaseAgent): The agent to run.
            previous_output (Optional[BaseResponse]): The output from the previous iteration.
            iteration_num (int): The current iteration number.

        Returns:
            Tuple[BaseResponse, bool]: The response from the agent and a flag indicating if the phase is complete.
        """
        pass

    @property
    def name(self):
        return "BasePhase"