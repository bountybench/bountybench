import asyncio
from pathlib import Path

from agents.prompts import TARGET_HOST_PATCH_PROMPT, PATCH_PROMPT, STOP_TOKEN
from phases.patch_phase import PatchPhase
from resources.utils import read_writeup
from workflows.bounty_workflow import BountyWorkflow

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class PatchWorkflow(BountyWorkflow):
    """Workflow for patching vulnerabilities"""
    
    def _create_phases(self):
        """Define and register phases specific to PatchWorkflow."""

        phase_kwargs = {
            'model': self.params.get('model'),
            'bounty_number': self.bounty_number,
            'max_iterations': 20,
            'use_agent_exploit': False
        }
        if hasattr(self, "phase_iterations"):
            phase_kwargs["max_iterations"] = self.phase_iterations

        phase_kwargs["interactive"] = self.interactive
        
        patch_phase = PatchPhase(workflow=self, **phase_kwargs)

        self._register_root_phase(patch_phase)

    def _get_initial_prompt(self) -> str:
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """
        exploit_report = read_writeup(self.task_dir, self.bounty_number)
        if self.repo_metadata["target_host"]: 
            prompt = TARGET_HOST_PATCH_PROMPT.format(
                task_description=exploit_report,
                stop_token=STOP_TOKEN,
                target_host=self.repo_metadata["target_host"],
            )
        else: 
            prompt = PATCH_PROMPT.format(
                task_description=exploit_report,
                stop_token=STOP_TOKEN
            )
        return prompt

async def main() -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run the patch workflow")
    parser.add_argument("--task_dir", type=str, help="The directory of the task repo", required=True)
    parser.add_argument("--bounty_number", type=str, help="The bounty number", required=True)
    parser.add_argument("--interactive", action="store_true", help="Enable interactive mode")
    parser.add_argument("--model", type=str, help="The LM model to query")
    parser.add_argument("--phase_iterations", type=int, help="max iteractions to run of PatchPhase")
    args = parser.parse_args()

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Run workflow
    workflow = PatchWorkflow(task_dir=Path(args.task_dir), bounty_number=args.bounty_number, interactive=args.interactive, model=args.model, phase_iterations=args.phase_iterations)
    await workflow.run()

if __name__ == "__main__":
    asyncio.run(main())
