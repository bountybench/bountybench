import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

from agents.base_agent import AgentConfig
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.executor_agent.prompt import PATCH_PROMPT, STOP_TOKEN
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from phases.base_phase import PhaseConfig
from phases.patch_phase import PatchPhase
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.utils import read_exploit_report
from workflows.base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)

class PatchWorkflow(BaseWorkflow):
    """Workflow for patching vulnerabilities"""
    PHASES = [PatchPhase]  # Define required phases

    def __init__(self, task_repo_dir: Path, bounty_number: str, interactive: bool = False):
        workflow_id = "patch_workflow"
        super().__init__(task_repo_dir, bounty_number, workflow_id, interactive)
        self.patch_files_path: Optional[str] = None

    def define_phases(self):
        """Define and register phases specific to PatchWorkflow."""
        # Initialize PatchPhase with its PhaseConfig
        patch_phase_config = PhaseConfig(
            # phase_name="PatchPhase", # can optionally set, otherwise uses defaults
            max_iterations=25, # Later will be cmdline arg
            # agent_configs=self.get_patch_agent_configs(), # can optionally set, otherwise uses defaults
            interactive=False # cmdline arg
        )

        patch_phase = PatchPhase(
            phase_config=patch_phase_config,
            agent_manager=self.agent_manager,
            workflow=self,
            initial_response=None  # Or pass an appropriate initial response if needed
        )

        # Register the PatchPhase
        self.register_phase(patch_phase)
        logger.info(f"PatchPhase registered with config: {patch_phase_config}")

    def get_initial_prompt(self) -> str:
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """
        exploit_report = read_exploit_report(self.task_repo_dir, self.bounty_number)
        prompt = PATCH_PROMPT.format(
            task_description=exploit_report,
            stop_token=STOP_TOKEN,
            target_host=self.repo_metadata.get("target_host", "localhost"),
        )
        return prompt

    def setup_directories(self) -> None:
        """No necessary directories for this workflow."""
        pass

def main() -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run the patch workflow")
    parser.add_argument("--task_repo_dir", type=str, help="The directory of the task repo", required=True)
    parser.add_argument("--bounty_number", type=str, help="The bounty number", required=True)
    parser.add_argument("--interactive", action="store_true", help="Enable interactive mode")
    args = parser.parse_args()

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Run workflow
    workflow = PatchWorkflow(Path(args.task_repo_dir), args.bounty_number, interactive=args.interactive)
    workflow.run()

if __name__ == "__main__":
    main()
