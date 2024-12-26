import os
from pathlib import Path
from typing import Optional

from agents.dataclasses.agent_spec import AgentConfig
from agents.patch_agent.patch_agent import PatchAgent
from agents.executor_agent.prompt import PATCH_PROMPT, STOP_TOKEN
from agents.executor_agent.executor_agent import ExecutorAgent
from phases.base_phase import BasePhase, PhaseConfig
from phases.patch_phase import PatchPhase
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.setup_resource import SetupResource
from resources.utils import docker_network_exists, run_command, read_repo_metadata, read_bounty_metadata
from responses.response import Response
from responses.answer_response_interface import AnswerResponseInterface
from utils.logger import get_main_logger
from utils.workflow_logger import workflow_logger
from workflows.base_workflow import BaseWorkflow, WorkflowConfig

logger = get_main_logger(__name__)

class PatchWorkflow(BaseWorkflow):
    """Workflow for patching vulnerabilities"""
    
    def __init__(self, task_repo_dir: Path, bounty_number: str):
        self.task_repo_dir = task_repo_dir
        self.bounty_number = bounty_number
        self.repo_metadata = read_repo_metadata(str(task_repo_dir))
        self.bounty_metadata = read_bounty_metadata(str(task_repo_dir), bounty_number)
        
        # Validate patch is available
        if not self.bounty_metadata['patch']:
            raise ValueError(f"Patching not available for {task_repo_dir.name}")
            
        # Setup workflow config
        config = WorkflowConfig(
            name="patch_workflow",
            max_iterations=25,
            logs_dir=Path("logs"),
            task_repo_dir=task_repo_dir,
            bounty_number=int(bounty_number),
            metadata={
                "repo_metadata": self.repo_metadata,
                "bounty_metadata": self.bounty_metadata
            }
        )
        super().__init__(config)
        
        # Store workflow-specific data
        self.vulnerable_files = []
        self.exploit_description = ""
        self.executor_agent = None
        self.patch_agent = None

    def setup_init(self) -> None:
        """Setup initial state of the workflow"""
        network_name = "shared_net"
        if not docker_network_exists(network_name):
            logger.info(f"Creating Docker network: {network_name}")
            run_command(["docker", "network", "create", network_name])

        vulnerable_commit = self.bounty_metadata['vulnerable_commit']
        run_command(["git", "checkout", vulnerable_commit], str(self.task_repo_dir) + "/codebase")
        
        for _, value in self.bounty_metadata['patch'].items():
            relative_path = os.path.relpath(value, start="codebase")
            full_path = os.path.join(str(self.task_repo_dir), value)
            if os.path.exists(full_path):
                self.vulnerable_files.append(relative_path)
        
        run_command(["git", "checkout", "main"], str(self.task_repo_dir) + "/codebase")

        self.workflow_logger.add_metadata("vulnerable_files", self.vulnerable_files)
        self.workflow_logger.add_metadata("exploit_description", self.exploit_description)
        

    def setup_resources(self) -> None:
        """Setup all required resources"""
        files_dir, tmp_dir = "codebase", "tmp"
        exploit_files_dir = os.path.join("bounties", f"bounty_{self.bounty_number}", "exploit_files")
        vulnerable_commit = self.bounty_metadata['vulnerable_commit']
        
        # Initialize files
        InitFilesResource(
            task_repo_dir=self.task_repo_dir,
            files_dir_name=files_dir,
            tmp_dir_name=tmp_dir,
            exploit_files_dir_name=exploit_files_dir,
            vulnerable_commit=vulnerable_commit
        )
        
        # Setup repository environment if needed
        if os.path.exists(str(self.task_repo_dir) + "/setup_repo_env.sh"):
            SetupResource(task_level_setup=False, task_repo_dir=self.task_repo_dir, files_dir=files_dir)
            
        # Setup target host if specified
        if self.repo_metadata["target_host"]:
            SetupResource(
                task_level_setup=True,
                task_repo_dir=self.task_repo_dir,
                files_dir=files_dir,
                bounty_number=self.bounty_number,
                server_address=self.repo_metadata["target_host"]
            )
            
        # Setup Kali environment and Docker
        KaliEnvResource(
            "KaliEnv",
            task_repo_dir=self.task_repo_dir,
            bounty_number=self.bounty_number,
            volumes={os.path.join(str(self.task_repo_dir.absolute()), tmp_dir): {"bind": "/app", "mode": "rw"}}
        )
        DockerResource("DockerHelper")

    def setup_agents(self) -> None:
        """Setup and configure agents"""
        # Format exploit description
        vulnerable_files_formatted = ", ".join(f"`{file}`" for file in self.vulnerable_files)
        self.exploit_description = f"""
        {self.bounty_metadata["exploit_prompt"]} 
        The path to the vulnerable file(s) is {vulnerable_files_formatted}. 
        """
        
        # Configure and create agents
        executor_agent_config = AgentConfig(
            model='openai/o3-mini-2024-12-17',
            max_output_tokens=25000,
            max_input_tokens=25000,
            max_iterations=25,
            max_iterations_stored_in_memory=3,
            use_helm=False
        )
        
        patch_prompt = PATCH_PROMPT.format(
            task_description=self.exploit_description,
            stop_token=STOP_TOKEN,
            target_host=self.repo_metadata["target_host"],
        )
        
        self.executor_agent = ExecutorAgent(
            config=executor_agent_config,
            initial_prompt=patch_prompt,
            logger=self.workflow_logger,
            target_host=self.repo_metadata["target_host"]
        )
        self.workflow_logger.add_agent("ExecutorAgent", self.executor_agent)
        
        self.patch_agent = PatchAgent(bounty_dir=os.path.join("bounties", f"bounty_{self.bounty_number}"))
        self.workflow_logger.add_agent("PatchAgent", self.patch_agent)

    def setup_phases(self) -> None:
        super().setup_phases()

        # Configure patch phase
        phase_config = PhaseConfig(
            phase_idx=0,
            phase_name="patch",
            max_iterations=25,
            agents=[
                ("executor_agent", self.executor_agent),
                ("patch_agent", self.patch_agent)
            ]
        )
        self.config.phase_configs.append(phase_config)

    def create_phase(self, phase_config: PhaseConfig, prev_response: Optional[Response]) -> BasePhase:
        """Create patch phase instance"""
        return PatchPhase(phase_config, prev_response)

def main() -> None:
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the patch workflow")
    parser.add_argument("--task_repo_dir", type=str, help="The directory of the task repo")
    parser.add_argument("--bounty_number", type=str, help="The bounty number")
    args = parser.parse_args()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Run workflow
    workflow = PatchWorkflow(Path(args.task_repo_dir), args.bounty_number)
    workflow.run()

if __name__ == "__main__":
    main()
