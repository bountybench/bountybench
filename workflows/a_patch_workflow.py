import os
from pathlib import Path

from agents.dataclasses.agent_lm_spec import AgentLMConfig
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.executor_agent.prompt import PATCH_PROMPT, STOP_TOKEN
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from phases.base_phase import PhaseConfig
from phases.patch_phase import PatchPhase
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.utils import read_exploit_report
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow
#handling of optional resources todo

class PatchWorkflow(BaseWorkflow):
    """Workflow for patching vulnerabilities"""
    PHASES = [PatchPhase]
    # Agents = ExecutorAgent, PatchAgent
    # Resource =  KaliEnvResource, DockerResource (InitFilesResource, (maybe SetupFilesResource (2x)) handled in super)
    
    def __init__(self, task_repo_dir: Path, bounty_number: str, interactive: bool=False):
        workflow_id = "patch_workflow"
        super().__init__(task_repo_dir, bounty_number, workflow_id, interactive)

    ################################
    def define_phases(self) -> None:
        """Configure phases"""
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
        self.register_phase(PatchPhase, phase_config)

    def define_agents(self) -> None:
        """Configure agents"""
        executor_lm_agent_config = AgentLMConfig(
            model='openai/o3-mini-2024-12-17',
            max_output_tokens=25000,
            max_input_tokens=25000,
            max_iterations=25,
            max_iterations_stored_in_memory=3,
            use_helm=False
        )

        executor_agent_config = ExecutorAgentConfig(
            config=executor_lm_agent_config,
            logger=self.workflow_logger,
            target_host=self.repo_metadata["target_host"]
        )
        self.register_agent("ExecutorAgent", ExecutorAgent, executor_agent_config)
        
        patch_agent_config = PatchAgentConfig(
            bounty_dir=os.path.join("bounties", f"bounty_{self.bounty_number}")
            )
        self.register_agent("PatchAgent", PatchAgent, patch_agent_config)
        
    def define_resources(self):
        super().__init__(self)
        
        tmp_dir = os.path.join(str(self.task_repo_dir), "tmp")
        self.patch_files_path = os.path.join(tmp_dir, "patch_files")

        os.makedirs(self.patch_files_path, exist_ok=True)
        logger.info(f"Created patch_files directory at: {self.patch_files_path}")

        kali_env_config = KaliEnvResourceConfig(
            task_repo_dir=self.task_repo_dir,
            bounty_number=self.bounty_number,
            volumes={
                os.path.abspath(os.path.join(str(self.task_repo_dir), tmp_dir)): {"bind": "/app", "mode": "rw"},
                os.path.abspath(self.patch_files_path): {"bind": "/app/patch_files", "mode": "rw"},
                "/tmp": {"bind": "/tmp", "mode": "rw"}
            }
        )
        self.register_resource("KaliEnv", KaliEnvResource, kali_env_config)

        docker_config = DockerResourceConfig()
        self.register_resource("DockerHelper", DockerResource, docker_config)
    ###############################    

    def get_initial_prompt(self):
        exploit_report = read_exploit_report(self.task_repo_dir, self.bounty_number)
        prompt = PATCH_PROMPT.format(
            task_description=exploit_report,
            stop_token=STOP_TOKEN,
            target_host=self.repo_metadata["target_host"],
        )
    
        return prompt

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
