import os
from pathlib import Path

from agents.dataclasses.agent_lm_spec import AgentLMConfig
from agents.exploit_agent.exploit_agent import ExploitAgentConfig
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.executor_agent.prompt import DETECT_AND_PATCH_PROMPT, STOP_TOKEN
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from phases.base_phase import PhaseConfig
from phases.detect_phase import DetectPhase
from phases.exploit_phase import ExploitAgent, ExploitPhase
from phases.patch_phase import PatchPhase
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.utils import *
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow

logger = get_main_logger(__name__)

class DetectAndPatchWorkflow(BaseWorkflow):
    """Workflow for exploiting and patching vulnerabilities"""
    
    PHASES = [DetectPhase, ExploitPhase, PatchPhase]
    # Agents = ExecutorAgent, ExploitAgent, PatchAgent
    # Resource =  KaliEnvResource, DockerResource (InitFilesResource, (maybe SetupFilesResource (2x)) handled in super)
    exploit_files_path = None
    patch_files_path = None

    def __init__(self, task_repo_dir: Path, bounty_number: str, ref_task_repo_dir: Path, ref_bounty_number: str, interactive: bool = False):
        workflow_id = "exploit_and_patch_workflow"
        super().__init__(task_repo_dir, bounty_number, workflow_id, interactive)
        self.ref_task_repo_dir = ref_task_repo_dir
        self.ref_bounty_number = ref_bounty_number
        
    ######################################################
    def define_phases(self) -> None:
        """Define workflow phase configs"""
        detect_config = PhaseConfig(
            phase_idx=0,
            phase_name="detect",
            max_iterations=5,
            agents=[
                ("executor_agent", None)
            ],
            interactive=self.interactive
        )
        self.register_phase(DetectPhase, detect_config)

        exploit_config = PhaseConfig(
            phase_idx=0,
            phase_name="exploit",
            max_iterations=5,
            agents=[
                ("executor_agent", None),
                ("exploit_agent", None)
            ],
            interactive=self.interactive
        )
        self.register_phase(ExploitPhase, exploit_config)

        phase_config = PhaseConfig(
            phase_idx=1,
            phase_name="patch",
            max_iterations=3,
            agents=[
                ("executor_agent", self.executor_agent),
                ("patch_agent", self.patch_agent)
            ],
            interactive=self.interactive
        )
        self.register_phase(PatchPhase, phase_config)
    
    def define_agents(self) -> None:
        """Configure agents"""
        executor_agent_lm_config = AgentLMConfig(
            model='openai/o3-mini-2024-12-17',
            max_output_tokens=25000,
            max_input_tokens=25000,
            max_iterations=25,
            max_iterations_stored_in_memory=3,
            use_helm=False
        )
        executor_agent_config = ExecutorAgentConfig(
            config=executor_agent_lm_config,
            logger=self.workflow_logger,
            target_host=self.repo_metadata["target_host"]
        )
        self.register_agent("ExecutorAgent", ExecutorAgent, executor_agent_config)
                
        exploit_agent_config = ExploitAgentConfig(
            bounty_dir=os.path.join("bounties", f"bounty_{self.bounty_number}")
            )
        self.register_agent("ExploitAgent", ExploitAgent, exploit_agent_config)

        patch_agent_config = PatchAgentConfig(
            bounty_dir=os.path.join("bounties", f"bounty_{self.bounty_number}")
            )
        self.register_agent("PatchAgent", PatchAgent, patch_agent_config)

    def define_resources(self) -> None:
        super().__init__(self)
                
        # Setup Kali environment and Docker
        kali_env_config = KaliEnvResourceConfig(
            task_repo_dir=self.task_repo_dir,
            bounty_number=self.bounty_number,
            volumes={
                os.path.abspath(os.path.join(str(self.task_repo_dir), tmp_dir)): {"bind": "/app", "mode": "rw"},
                os.path.abspath(self.exploit_files_path): {"bind": "/app/exploit_files", "mode": "rw"},
                os.path.abspath(self.patch_files_path): {"bind": "/app/patch_files", "mode": "rw"},
                "/tmp": {"bind": "/tmp", "mode": "rw"}
            }
        )
        self.register_resource("KaliEnv", KaliEnvResource, kali_env_config)

        docker_config = DockerResourceConfig()
        self.register_resource("DockerHelper", DockerResource, docker_config)
    ######################################################

    def get_initial_prompt(self):
        ref_exploit_report = read_exploit_report(self.ref_task_repo_dir, self.ref_bounty_number)
        prompt = DETECT_AND_PATCH_PROMPT.format(
            task_description=ref_exploit_report,
            stop_token=STOP_TOKEN,
            target_host=self.repo_metadata["target_host"],
        )
        return prompt

    # def setup_directories(self):
    #     tmp_dir = os.path.join(str(self.task_repo_dir), "tmp")
    #     self.exploit_files_path = os.path.join(tmp_dir, "exploit_files")

    #     os.makedirs(self.exploit_files_path, exist_ok=True)
        
    #     logger.info(f"Created exploit_files directory at: {self.exploit_files_path}")

def main() -> None:
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the exploit and patch workflow")
    parser.add_argument("--task_repo_dir", type=str, help="The directory of the task repo")
    parser.add_argument("--bounty_number", type=str, help="The bounty number")

    parser.add_argument("--ref_task_repo_dir", type=str, help="The directory of the reference task repo")
    parser.add_argument("--ref_bounty_number", type=str, help="The reference task bounty number")

    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    args = parser.parse_args()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Run workflow
    workflow = DetectAndPatchWorkflow(Path(args.task_repo_dir), args.bounty_number, Path(args.ref_task_repo_dir), args.ref_bounty_number, args.interactive)
    workflow.run()

if __name__ == "__main__":
    main()
