from abc import ABC, abstractmethod
from dataclasses import field
from enum import Enum
import os
from typing import Dict, Any, List
from pathlib import Path
from agents.base_agent import BaseAgent, AgentConfig
from phases.base_phase import BasePhase, PhaseConfig
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.docker_resource import dataclass
from resources.resource_manager import ResourceManager, Type
from resources.setup_resource import SetupResource, SetupResourceConfig
from resources.utils import docker_network_exists, read_bounty_metadata, read_repo_metadata, run_command

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
    metadata: Dict[str, Any] = field(default_factory=dict)
    phase_configs: List[PhaseConfig] = field(default_factory=list)

class BaseWorkflow(ABC):
    """
    Base class for defining workflows that coordinate phases and their agents.
    
    A workflow:
    - Acts as top-level controller for phases
    - Manages workflow-level logging
    - Coordinates phase transitions and data flow between phases
    - Tracks overall workflow state and completion status
    """
    # PHASES = []

    def __init__(self, task_repo_dir: Path, bounty_number: str, workflow_id: Optional[str] = "base_workflow", interactive: Optional[bool] = False):
        """Initialize workflow with configuration"""
        self.task_repo_dir = task_repo_dir
        self.bounty_number = bounty_number
        self.repo_metadata = read_repo_metadata(str(task_repo_dir))
        self.bounty_metadata = read_bounty_metadata(str(task_repo_dir), bounty_number)
        
        # Setup workflow config
        config = WorkflowConfig(
            id=workflow_id,
            max_iterations=25,
            logs_dir=Path("logs"),
            task_repo_dir=task_repo_dir,
            bounty_number=int(bounty_number),
            metadata={
                "repo_metadata": self.repo_metadata,
                "bounty_metadata": self.bounty_metadata
            }
        )

        self.config = config
        self.status = WorkflowStatus.INITIALIZED
        self._current_phase_idx = 0
        self._workflow_iteration_count = 0
        
        # Initialize workflow logger
        # self.workflow_logger = workflow_logger
        # self.workflow_logger.initialize(
        #     workflow_id=config.id,
        #     logs_dir=str(config.logs_dir),
        #     task_repo_dir=str(config.task_repo_dir),
        #     bounty_number=str(config.bounty_number)
        # )
        
        # Add workflow metadata
        # for key, value in config.metadata.items():
        #     self.workflow_logger.add_metadata(key, value)
        
        self.setup_init()
        self.define_resources()
        self.define_agents()
        self.define_phases()
        self._compute_schedule()


    @abstractmethod
    def get_initial_prompt(self):
        pass


    @abstractmethod
    def define_resources(self):
        # Universal across all task setup: InitFilesResource and SetupResource(s)
        files_dir, tmp_dir = "codebase", "tmp"
        exploit_files_dir = os.path.join("bounties", f"bounty_{self.bounty_number}", "exploit_files")
        vulnerable_commit = self.bounty_metadata['vulnerable_commit']
        
        # Initialize files
        init_files_config = InitFilesResourceConfig(
            task_repo_dir=self.task_repo_dir,
            files_dir_name=files_dir,
            tmp_dir_name=tmp_dir,
            exploit_files_dir_name=exploit_files_dir,
            vulnerable_commit=vulnerable_commit
        )
        self.register_resource("InitFiles", InitFilesResource, init_files_config)

        # Setup repository environment if needed
        if os.path.exists(str(self.task_repo_dir) + "/setup_repo_env.sh"):
            repo_env_config = SetupResourceConfig(
                task_level_setup=False, 
                task_repo_dir=self.task_repo_dir, 
                files_dir=files_dir
            )
            self.register_resource("RepoResource", SetupResource, repo_env_config)
            
        # Setup target host if specified
        if self.repo_metadata["target_host"]:
            task_server_config = SetupResourceConfig(
                task_level_setup=True,
                task_repo_dir=self.task_repo_dir,
                files_dir=files_dir,
                bounty_number=self.bounty_number,
                server_address=self.repo_metadata["target_host"]
            )
            self.register_resource("task_server", SetupResource, task_server_config)

    @abstractmethod
    def define_agents(self):
        pass

    @abstractmethod
    def define_phases(self):
        pass

    def _compute_schedule(self):
        self.resource_manager.compute_schedule(self.PHASES)

    def setup_phase_resources(self, phase_index: int) -> None:
        """Setup all required resources for a phase"""
        self.resource_manager.allocate_phase_resources(phase_index)

    def _takedown_phase_resources(self, phase_index: int) -> None:
        """Take down all resources no longer required in rest of the workflow"""
        self.resource_manager.deallocate_phase_resources(phase_index)

    def _create_agent(self):
        pass

    def setup_phase_agents(self, phase_index: int) -> None:
        """Setup and configure agents"""
        pass

    def _create_phase(self, phase_class: Type[BasePhase], phase_config: PhaseConfig):
        pass

    # def create_phase(self, phase_config: PhaseConfig, prev_response: Optional[Response]) -> BasePhase:
    #     """Create phase instance based on config"""
    #     if phase_config.phase_name == "exploit":
    #         return ExploitPhase(phase_config, prev_response)
    #     elif phase_config.phase_name == "patch":
    #         return PatchPhase(phase_config, prev_response)
    #     else:
    #         raise ValueError(f"Unknown phase: {phase_config.phase_name}")

    def setup_phase(self, phase_index: int) -> None:
        """
        Setup workflow phases and resources.
        This orchestrates the setup process in the correct order with logging.
        """
        try:
            self._setup_phase_resources(phase_index)
            self.setup_phase_agents(phase_index)
            create_phase

        except Exception as e:
            self.status = WorkflowStatus.INCOMPLETE
            raise e

    def _validate_phase_configs(self) -> None:
        """Validate phase configurations before execution"""
        if not self.config.phase_configs:
            raise ValueError("No phase configurations provided")
            
        # Validate phase numbers are sequential starting from 0
        phase_numbers = [p.phase_idx for p in self.config.phase_configs]
        if sorted(phase_numbers) != list(range(0, len(phase_numbers))):
            raise ValueError("Phase numbers must be sequential starting from 0")


    def setup_init(self) -> None:
        """Setup initial state of the workflow"""
        self.setup_network()
        self.setup_directories()
        self.setup_git_state()

    def _setup_network(self):
        network_name = "shared_net"
        if not docker_network_exists(network_name):
            logger.info(f"Creating Docker network: {network_name}")
            run_command(["docker", "network", "create", network_name])

    def _setup_git_state(self):
        vulnerable_commit = self.bounty_metadata['vulnerable_commit']
        run_command(["git", "checkout", vulnerable_commit], str(self.task_repo_dir) + "/codebase")
        
        for _, value in self.bounty_metadata['patch'].items():
            relative_path = os.path.relpath(value, start="codebase")
            full_path = os.path.join(str(self.task_repo_dir), value)
            if os.path.exists(full_path):
                self.vulnerable_files.append(relative_path)
        
        run_command(["git", "checkout", "main"], str(self.task_repo_dir) + "/codebase")

    def register_resource(self, resource_id:str, resource_class: Type[BaseResource], resource_config: BaseResourceConfig):
        self.resource_manager.register_resource(resource_id, resource_class, resource_config)
    
    def register_agent(self, agent_id:str, agent_class: Type[BaseAgent], agent_config: AgentConfig):
        self._agent_registration[agent_id] = (agent_class, agent_config)
        self.workflow_logger.add_agent(agent_id, self.patch_agent)

    def register_phase(self, phase_class: Type[BasePhase], phase_config: PhaseConfig):
        self.config.phase_configs.append(phase_class, phase_config) #wrong struct?






    """
    Update the code according to this comment: 
    Rather than just "run", you want to go phase by phase and use yield so that you can call next(workflow) and transition to run only a single phase. run can be an api where you continue runninguntil the end. This way you refactor the logic of running just a single phase vs running the netire workflow.
    """

    def run(self) -> None:
        """
        Execute the workflow by running phases in sequence.
        """
        try:
            self.setup_phases()
            self._validate_phase_configs()
            self.status = WorkflowStatus.INCOMPLETE
            
            prev_response = None
            
            # Execute phases in sequence
            for phase_idx, phase_config in enumerate(self.config.phase_configs):
                self._current_phase_idx = phase_idx
                
                # Create and run phase
                #setup phase
                phase = self.create_phase(phase_config, prev_response)
                phase_response, phase_success = phase.run_phase()
                
                # Update workflow state
                prev_response = phase_response
                if not phase_success:
                    self.status = WorkflowStatus.COMPLETED_FAILURE
                    break
                    
                self._iteration_count += 1
                if self._iteration_count >= self.config.max_iterations:
                    self.status = WorkflowStatus.COMPLETED_MAX_ITERATIONS
                    break
                    
            # If we completed all phases successfully
            if phase_success and phase_idx == len(self.config.phase_configs) - 1:
                self.status = WorkflowStatus.COMPLETED_SUCCESS
                
            # Finalize workflow
            self.workflow_logger.finalize(self.status.value)
            
        except Exception as e:
            self.status = WorkflowStatus.INCOMPLETE
            self.workflow_logger.finalize(self.status.value)
            raise e

    @property
    def current_phase(self) -> Optional[PhaseConfig]:
        """Get current phase configuration"""
        if 0 <= self._current_phase_idx < len(self.config.phase_configs):
            return self.config.phase_configs[self._current_phase_idx]
        return None