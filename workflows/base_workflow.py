from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

from enum import Enum
import logging

# Import your specific modules and classes here
from agents.base_agent import BaseAgent, AgentConfig
from phases.base_phase import BasePhase, PhaseConfig
from responses.base_response import BaseResponse
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.init_files_resource import InitFilesResourceConfig
from resources.init_files_resource import InitFilesResource
from resources.resource_manager import ResourceManager
from resources.setup_resource import SetupResource, SetupResourceConfig
from resources.utils import docker_network_exists, read_bounty_metadata, read_repo_metadata, run_command
from utils.workflow_logger import workflow_logger

# Initialize the module-level logger
logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Status of workflow execution"""
    INITIALIZED = "initialized"
    INCOMPLETE = "incomplete"
    COMPLETED_SUCCESS = "completed_success"
    COMPLETED_FAILURE = "completed_failure"
    COMPLETED_MAX_ITERATIONS = "completed_max_iterations"


@dataclass
class WorkflowConfig:
    """Configuration for a workflow"""
    id: str
    max_iterations: int
    logs_dir: Path
    task_repo_dir: Path
    bounty_number: int
    initial_prompt: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    phase_configs: List['PhaseConfig'] = field(default_factory=list)  



class BaseWorkflow(ABC):
    """
    Base class for defining workflows that coordinate phases and their agents.
    
    A workflow:
    - Acts as top-level controller for phases
    - Manages workflow-level logging
    - Coordinates phase transitions and data flow between phases
    - Tracks overall workflow state and completion status
    """

    def __init__(
        self,
        task_repo_dir: Path,
        bounty_number: str,
        workflow_id: Optional[str] = "base_workflow",
        interactive: Optional[bool] = False
    ):
        """Initialize workflow with configuration"""
        self.task_repo_dir = task_repo_dir
        self.bounty_number = str(bounty_number)  # Ensure it's an integer
        self.repo_metadata = read_repo_metadata(str(task_repo_dir))
        self.bounty_metadata = read_bounty_metadata(str(task_repo_dir), str(self.bounty_number))
        
        # Setup workflow config
        config = WorkflowConfig(
            id=workflow_id,
            max_iterations=25,
            logs_dir=Path("logs"),
            task_repo_dir=task_repo_dir,
            bounty_number=self.bounty_number,
            initial_prompt=self.get_initial_prompt(),
            metadata={
                "repo_metadata": self.repo_metadata,
                "bounty_metadata": self.bounty_metadata
            }
        )

        self.config = config
        self.status = WorkflowStatus.INITIALIZED
        self._current_phase_idx = 0
        self._workflow_iteration_count = 0

        self.workflow_logger = workflow_logger
        self.workflow_logger.initialize(
            workflow_name=config.id,
            logs_dir=str(config.logs_dir),
            task_repo_dir=str(config.task_repo_dir),
            bounty_number=str(config.bounty_number)
        )

        # Add workflow metadata
        for key, value in config.metadata.items():
            self.workflow_logger.add_metadata(key, value)

        # Initialize ResourceManager
        self.resource_manager = ResourceManager()

        # Initialize tracking structures
        self.agents: Dict[str, BaseAgent] = {}  # Maps agent_id to agent_instance
        self.phases: List[BasePhase] = []       # List to store phase instances
        self.phase_class_map = {}

        # Initialize additional attributes
        self.vulnerable_files: List[str] = []

        # Setup workflow
        self.setup_init()
        self.define_resource_configs()
        self.define_agent_configs()
        self.define_phase_configs()
        self._compute_schedule()

    @abstractmethod
    def get_initial_prompt(self) -> str:
        """Provide the initial prompt for the workflow."""
        pass

    @abstractmethod
    def define_agent_configs(self) -> None:
        """Define and register all agents required for the workflow."""
        pass

    @abstractmethod
    def define_phase_configs(self) -> None:
        """Define and register all phases required for the workflow."""
        pass

    def _compute_schedule(self) -> None:
        """
        Compute the resource usage schedule across all phases.
        Populates the phase_resources and resource_lifecycle dictionaries in ResourceManager.
        """
        phase_classes = [self.phase_class_map[phase_config.phase_name] for phase_config in self.config.phase_configs]
        self.resource_manager.compute_schedule(phase_classes)
        logger.debug("Computed resource schedule for all phases.")

    def setup_phase(self, phase_index: int, initial_response: Optional[BaseResponse] = None) -> None:
        """
        Setup a specific phase by allocating resources, setting up agents, and creating the phase instance.

        Args:
            phase_index (int): The index of the phase to set up.
        """
        try:
            logger.info(f"Setting up phase {phase_index} with initial response {initial_response}")
            
            # Step 1: Setup resources for the phase
            self.setup_phase_resources(phase_index)
            
            # Step 2: Setup agents for the phase
            self.setup_phase_agents(phase_index)
            
            # Step 3: Create the phase instance
            phase_instance = self._create_phase(phase_index, initial_response)
            
            logger.info(f"Phase {phase_index} setup complete: {phase_instance.__class__.__name__}")
            return phase_instance
        
        except Exception as e:
            self.status = WorkflowStatus.INCOMPLETE
            logger.error(f"Failed to set up phase {phase_index}: {e}")
            raise

    def setup_phase_agents(self, phase_index: int) -> None:
        """
        Setup and configure agents for a given phase.

        Args:
            phase_index (int): The index of the phase for which to set up agents.
        """
        try:
            # Retrieve the PhaseConfig for the given index
            phase_config = self.config.phase_configs[phase_index]
            logger.debug(f"Setting up agents for phase {phase_index}: {phase_config.phase_name}")

            # Register resources for each agent
            for agent_id, agent_instance in phase_config.agents:
                agent_instance.register_resources()
                logger.info(f"Registered resources for agent '{agent_id}' in phase {phase_index}")

        except IndexError:
            logger.error(f"No PhaseConfig found for phase index: {phase_index}")
            raise
        except Exception as e:
            logger.error(f"Error setting up agents for phase {phase_index}: {e}")
            raise

    def setup_phase_resources(self, phase_index: int) -> None:
        """
        Setup all required resources for a phase by allocating them through the ResourceManager.

        Args:
            phase_index (int): The index of the phase for which to allocate resources.
        """
        try:
            self.resource_manager.initialize_phase_resources(phase_index)
            logger.info(f"Resources allocated for phase {phase_index}")
        except Exception as e:
            logger.error(f"Error allocating resources for phase {phase_index}: {e}")
            raise

    def takedown_phase_resources(self, phase_index: int) -> None:
        """
        Setup all required resources for a phase by allocating them through the ResourceManager.

        Args:
            phase_index (int): The index of the phase for which to allocate resources.
        """
        try:
            self.resource_manager.deallocate_phase_resources(phase_index)
            logger.info(f"Relevant resources deallocated after phase {phase_index}")
        except Exception as e:
            logger.error(f"Error deallocating resources after phase {phase_index}: {e}")
            raise

    def create_agent(self, agent_class: Type[BaseAgent], agent_config: AgentConfig) -> BaseAgent:
        """
        Creates and registers an agent.

        Args:
            agent_class (Type[BaseAgent]): The class of the agent to instantiate.
            agent_config (AgentConfig): The configuration for the agent.

        Returns:
            BaseAgent: The instantiated agent.
        """
        try:
            # Instantiate the agent
            agent_instance = agent_class(agent_config=agent_config, resource_manager=self.resource_manager)
            
            # Register the agent in the agents dictionary
            self.agents[agent_config.id] = agent_instance
            logger.info(self.agents[agent_config.id])
            setattr(self, agent_config.id, agent_instance)
            
            # Log the creation
            logger.debug(f"Created agent: {agent_config.id} of type {agent_class.__name__}")
            
            return agent_instance
        except Exception as e:
            logger.error(f"Failed to create agent '{agent_config}': {e}")
            raise

    def _create_phase(self, phase_index: int, initial_response: Optional[BaseResponse] = None) -> BasePhase:
        """
        Creates an instance of a phase based on its configuration.

        Args:
            phase_index (int): The index of the phase to create.

        Returns:
            BasePhase: The instantiated phase.
        """
        try:
            phase_config = self.config.phase_configs[phase_index]
            phase_class = self.phase_class_map[phase_config.phase_name]
            phase_instance = phase_class(phase_config=phase_config, initial_response=initial_response)
            self.phases.append(phase_instance)
            logger.debug(f"Created phase: {phase_class.__name__} for Workflow ID: {self.config.id}")
            return phase_instance
        except Exception as e:
            logger.error(f"Failed to create phase at index {phase_index}: {e}")
            raise

    def _validate_phase_configs(self) -> None:
        """
        Validate phase configurations before execution.
        Ensures that phase indices are sequential starting from 0.
        """
        if not self.config.phase_configs:
            raise ValueError("No phase configurations provided")
            
        # Validate phase indices are sequential starting from 0
        phase_indices = [phase_config.phase_idx for phase_config in self.config.phase_configs]
        expected_indices = list(range(len(phase_indices)))
        if sorted(phase_indices) != expected_indices:
            raise ValueError("Phase indices must be sequential starting from 0")
        
        logger.debug("Phase configurations validated successfully.")

    def setup_init(self) -> None:
        """Setup initial state of the workflow."""
        self.setup_network()
        self.setup_directories()
        self.setup_git_state()
        # self.log_metadata()

    def setup_network(self) -> None:
        """Setup Docker network if it does not exist."""
        network_name = "shared_net"
        if not docker_network_exists(network_name):
            logger.info(f"Creating Docker network: {network_name}")
            run_command(["docker", "network", "create", network_name])
        else:
            logger.debug(f"Docker network '{network_name}' already exists.")

    def setup_git_state(self) -> None:
        """Setup Git state by checking out the vulnerable commit and identifying vulnerable files."""
        vulnerable_commit = self.bounty_metadata.get('vulnerable_commit', 'main')
        codebase_path = os.path.join(str(self.task_repo_dir), "codebase")
        
        logger.info(f"Checking out vulnerable commit: {vulnerable_commit}")
        run_command(["git", "checkout", vulnerable_commit], codebase_path)
        
        for _, value in self.bounty_metadata.get('patch', {}).items():
            relative_path = os.path.relpath(value, start="codebase")
            full_path = os.path.join(str(self.task_repo_dir), value)
            if os.path.exists(full_path):
                self.vulnerable_files.append(relative_path)
                logger.debug(f"Identified vulnerable file: {relative_path}")
        
        logger.info("Checking out main branch.")
        run_command(["git", "checkout", "main"], codebase_path)

    @abstractmethod
    def setup_directories(self) -> None:
        """Setup necessary directories for the workflow."""
        pass

    # @abstractmethod
    # def log_metadata(self) -> None:
    #     """Log workflow metadata."""
    #     pass

    def register_resource(
        self,
        resource_id: str,
        resource_class: Type[BaseResource],
        resource_config: BaseResourceConfig
    ) -> None:
        """
        Registers a resource with the ResourceManager.

        Args:
            resource_id (str): The unique identifier for the resource.
            resource_class (Type[BaseResource]): The class of the resource.
            resource_config (BaseResourceConfig): The configuration for the resource.
        """
        self.resource_manager.register_resource(resource_id, resource_class, resource_config)
        logger.debug(f"Registered resource '{resource_id}' with class '{resource_class.__name__}'")

    def register_agent(
        self,
        agent_class: Type[BaseAgent],
        agent_config: AgentConfig
    ) -> None:
        """
        Registers an agent with the workflow.

        Args:
            agent_id (str): The unique identifier for the agent.
            agent_class (Type[BaseAgent]): The class of the agent.
            agent_config (AgentConfig): The configuration for the agent.
        """
        # Instantiate and register the agent
        agent_instance = self.create_agent(agent_class, agent_config)
        logger.debug(f"Registered agent '{agent_config.id}' of type '{agent_class.__name__}'")

    def define_resource_configs(self) -> None:
        """
        Defines and registers all necessary resources for the workflow.
        """
        try:
            # Define resource directories and configurations by retrieving from metadata or providing defaults
            files_dir = self.bounty_metadata.get('files_dir', 'codebase')
            tmp_dir = self.bounty_metadata.get('tmp_dir', 'tmp')
            exploit_files_dir = self.bounty_metadata.get('exploit_files_dir', f'bounties/bounty_{self.bounty_number}/exploit_files')
            vulnerable_commit = self.bounty_metadata.get('vulnerable_commit', 'main')

            # Initialize InitFilesResource
            init_files_config = InitFilesResourceConfig(
                task_repo_dir=self.task_repo_dir,
                files_dir_name=files_dir,
                tmp_dir_name=tmp_dir,
                exploit_files_dir_name=exploit_files_dir,
                vulnerable_commit=vulnerable_commit
            )
            self.register_resource("init_files", InitFilesResource, init_files_config)
            logger.info("Registered 'init_files' resource.")

            # Setup repository environment if needed
            setup_repo_env_script = os.path.join(str(self.task_repo_dir), "setup_repo_env.sh")
            if os.path.exists(setup_repo_env_script):
                repo_env_config = SetupResourceConfig(
                    task_level_setup=False,
                    task_repo_dir=self.task_repo_dir,
                    files_dir=files_dir
                )
                self.register_resource("repo_resource", SetupResource, repo_env_config)
                logger.info("Registered 'repo_resource' for repository environment.")

            else:
                logger.debug("No repository environment setup script found.")

            # Setup target host if specified
            target_host = self.repo_metadata.get("target_host")
            if target_host:
                task_server_config = SetupResourceConfig(
                    task_level_setup=True,
                    task_repo_dir=self.task_repo_dir,
                    files_dir=files_dir,
                    bounty_number=self.bounty_number,
                    server_address=target_host
                )
                self.register_resource("task_server", SetupResource, task_server_config)
                logger.info(f"Registered 'task_server' for target host: {target_host}")
            else:
                logger.debug("No target host specified in repository metadata.")

        except Exception as e:
            logger.error(f"Failed to define resources: {e}")
            raise

    def register_phase(
        self,
        phase_class: Type[BasePhase],
        phase_specific_config: Any,
        agents: List[Tuple[str, BaseAgent]],
    ) -> None:
        """
        Registers a phase with its configuration and associated agents.

        Args:
            phase_class (Type[BasePhase]): The class of the phase to register.
            phase_specific_config (Any): The specific configuration for the phase.
            agents (List[Tuple[str, BaseAgent]]): A list of tuples containing agent IDs and their instances.
        """
        # Validate that agents are provided
        if not agents:
            raise ValueError(f"No agents provided for phase '{phase_class.__name__}'.")

        # Validate phase-specific config has required attributes
        if not hasattr(phase_specific_config, "max_iterations"):
            raise ValueError("Phase-specific config must have 'max_iterations' defined.")

        # Add the phase class to the phase_class_map if not already present
        phase_name = phase_class.__name__
        if phase_name not in self.phase_class_map:
            self.phase_class_map[phase_name] = phase_class

        # Create the phase configuration
        phase_config_instance = PhaseConfig(
            phase_idx=len(self.config.phase_configs),
            phase_name=phase_name,
            max_iterations=phase_specific_config.max_iterations,
            agents=agents,
        )

        # Append the phase configuration
        self.config.phase_configs.append(phase_config_instance)

        # Log the registration
        agent_ids = [agent_id for agent_id, _ in agents]
        logger.debug(
            f"Registered phase '{phase_name}' at index {phase_config_instance.phase_idx} "
            f"with agents: {agent_ids} and config: {phase_specific_config}"
        )

    def run_phases(self):
        """
        Generator that executes workflow phases one at a time.
        Yields (phase_response, phase_success) after each phase execution.
        """
        try:
            # self.setup_phases()
            self._validate_phase_configs()
            self.status = WorkflowStatus.INCOMPLETE
            
            prev_response = None
            if hasattr(self.config, "initial_prompt") and self.config.initial_prompt:
                prev_response = BaseResponse(self.config.initial_prompt)

            # Execute phases in sequence
            for phase_idx, phase_config in enumerate(self.config.phase_configs):
                self._current_phase_idx = phase_idx
                
                # Create and run phase
                phase = self.setup_phase(phase_idx, prev_response)
                logger.info(f"Phase {phase.phase_config.phase_name} set up")
                phase_response, phase_success = phase.run_phase()
                
                # Update workflow state
                prev_response = phase_response
                if not phase_success:
                    self.status = WorkflowStatus.COMPLETED_FAILURE
                    yield phase_response, phase_success
                    break
                    
                self._workflow_iteration_count += 1
                if self._workflow_iteration_count >= self.config.max_iterations:
                    self.status = WorkflowStatus.COMPLETED_MAX_ITERATIONS
                    yield phase_response, phase_success
                    break
                
                # Yield current phase results
                yield phase_response, phase_success
                self.takedown_phase_resources(phase_idx)
                    
            # If we completed all phases successfully
            if phase_success and phase_idx == len(self.config.phase_configs) - 1:
                self.status = WorkflowStatus.COMPLETED_SUCCESS
                
            # Finalize workflow
            self.workflow_logger.finalize(self.status.value)
            
        except Exception as e:
            self.status = WorkflowStatus.INCOMPLETE
            self.workflow_logger.finalize(self.status.value)
            raise e

    def run(self) -> None:
        """
        Execute the entire workflow by running all phases in sequence.
        This is a convenience method that runs the workflow to completion.
        """
        # Run through all phases
        for _ in self.run_phases():
            continue

    @property
    def current_phase(self) -> Optional[PhaseConfig]:
        """Get current phase configuration"""
        if 0 <= self._current_phase_idx < len(self.config.phase_configs):
            return self.config.phase_configs[self._current_phase_idx]
        return None