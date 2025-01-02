from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional, Set, Tuple, Type, Union

from agents.base_agent import AgentConfig, BaseAgent
from responses.base_response import BaseResponse
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
        self._initialize_agents()

    def get_phase_resources(self):
        phase_resources = {}
        for agent_class in self.AGENT_CLASSES:
            phase_resources.update(agent_class.REQUIRED_RESOURCES)
        return phase_resources

    def _initialize_agents(self):
        """Initialize and register required agents using AgentManager."""
        print(f"Debugging: Initializing agents for {self.name}")
        
        # First get agent configs
        self.phase_config.agent_configs = self.get_agent_configs()
        print(f"Debugging: Got agent configs: {[config[0] for config in self.phase_config.agent_configs]}")
        
        for agent_id, agent_config in self.phase_config.agent_configs:
            # Find matching agent class based on config type
            agent_class = next(
                (ac for ac in self.AGENT_CLASSES if isinstance(agent_config, ac.CONFIG_CLASS)), 
                None
            )
            
            if not agent_class:
                print(f"Warning: No matching agent class found for config type {type(agent_config)}")
                continue

            try:
                print(f"Debugging: Creating agent {agent_id} of type {agent_class.__name__}")
                agent_instance = self.agent_manager.get_or_create_agent(agent_id, agent_class, agent_config)
                self.agents.append((agent_id, agent_instance))
                print(f"Debugging: Successfully created agent {agent_id}")
            except Exception as e:
                print(f"Error creating agent {agent_id}: {str(e)}")
                raise

        # Verify all required agents present
        required_classes = set(self.AGENT_CLASSES)
        present_classes = {type(agent) for _, agent in self.agents}
        missing = required_classes - present_classes
        
        if missing:
            missing_names = ', '.join(agent.__name__ for agent in missing)
            raise ValueError(
                f"Phase '{self.phase_config.phase_name}' requires agents: {missing_names}. "
                f"Current agents: {[type(agent).__name__ for _, agent in self.agents]}"
            )
            
        if not self.agents:
            raise ValueError(
                f"No agents were initialized for phase {self.phase_config.phase_name}. "
                f"Expected agent classes: {[cls.__name__ for cls in self.AGENT_CLASSES]}"
            )
            
        print(f"Debugging: Completed agent initialization for {self.name}")

    def register_resources(self):
        """
        Register required resources with the ResourceManager.
        Should be called after resources are initialized for the phase.
        """
        print(f"Debugging: Registering resources for phase {self.phase_config.phase_idx} ({self.phase_config.phase_name})")
        for agent_id, agent in self.agents:
            print(f"Debugging: Registering resources for agent {agent_id}")
            agent.register_resources(self.resource_manager)
            
            workflow_logger.add_agent(agent.agent_config.id, agent)
        print(f"Debugging: Finished registering resources for phase {self.phase_config.phase_idx}")

    @classmethod
    def get_required_resources(cls) -> Set[str]:
        resources = set()
        for agent_cls in cls.AGENT_CLASSES:
            resources.update(agent_cls.get_required_resources())
        return resources

    def setup(self):
        """
        Initialize and register resources for the phase and its agents.
        Resources must be fully initialized before agents can access them.
        """
        print(f"Debugging: Entering setup for {self.name}")
        
        # 1. First define all resources
        resource_configs = self.define_resources()
        if not resource_configs:
            print("Warning: No resources defined in define_resources")
            return
            
        # 2. Register each resource
        for resource_id, (resource_class, resource_config) in resource_configs.items():
            print(f"Debugging: Registering resource {resource_id} of type {resource_class.__name__}")
            try:
                self.resource_manager.register_resource(resource_id, resource_class, resource_config)
            except Exception as e:
                print(f"Error registering resource {resource_id}: {str(e)}")
                raise
                
        # 3. Initialize all resources for this phase
        print("Debugging: Initializing all phase resources")
        try:
            self.resource_manager.initialize_phase_resources(
                phase_index=self.phase_config.phase_idx,
                resource_ids=resource_configs.keys()
            )
        except Exception as e:
            print(f"Error initializing phase resources: {str(e)}")
            raise
                
        # 4. Only after all resources are initialized, register them with agents
        print("Debugging: All resources initialized, registering with agents")
        for agent_id, agent in self.agents:
            print(f"Registering resources for agent {agent_id}")
            agent.register_resources(self.resource_manager)        
            workflow_logger.add_agent(agent.agent_config.id, agent)
            
        print(f"Debugging: Completed setup for {self.name}")


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

        # Initialize resources before starting iterations
        self.setup()

        # 1) Start phase context
        with workflow_logger.phase(self) as phase_ctx:
            for iteration_num in range(1, self.phase_config.max_iterations + 1):
                if self._done:
                    break

                agent_id, agent_instance = self._get_current_agent()

                if last_output:
                    print(f"Last output was {last_output.response}")
                else:
                    print("No last output")

                # 2) Start iteration context in the logger
                with phase_ctx.iteration(iteration_num, agent_id, last_output) as iteration_ctx:
                    response, done = self.run_one_iteration(
                        agent_instance=agent_instance,
                        previous_output=last_output,
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
        self, agent_instance: Any, previous_output: Optional[BaseResponse]
    ) -> Tuple[BaseResponse, bool]:
        """
        Run a single iteration of the phase.

        Args:
            agent_instance (BaseAgent): The agent to run.
            previous_output (Optional[BaseResponse]): The output from the previous iteration.

        Returns:
            Tuple[BaseResponse, bool]: The response from the agent and a flag indicating if the phase is complete.
        """
        pass

    @property
    def name(self):
        return "BasePhase"