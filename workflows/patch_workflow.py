import logging
from pathlib import Path

from agents.executor_agent.prompt import PATCH_PROMPT, STOP_TOKEN
from phases.patch_phase import PatchPhase
from resources.utils import read_exploit_report
from workflows.bounty_workflow import BountyWorkflow

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class PatchWorkflow(BountyWorkflow):
    """Workflow for patching vulnerabilities"""
    
    def _create_phases(self):
        """Define and register phases specific to PatchWorkflow."""
        init_prompt = self._get_initial_prompt()

        phase_kwargs = {
            'model': self.params.get('model'),
            'bounty_number': self.bounty_number,
            'initial_prompt': init_prompt,
            'max_iterations': 20
        }
        patch_phase = PatchPhase(workflow=self, **phase_kwargs)

        self._register_root_phase(patch_phase)

    def _get_initial_prompt(self) -> str:
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """
        exploit_report = read_exploit_report(self.task_dir, self.bounty_number)
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
    workflow = PatchWorkflow(task_dir=Path(args.task_dir), bounty_number=args.bounty_number, interactive=args.interactive, mode=args.model, phase_iterations=args.phase_iterations)
    workflow.run()

if __name__ == "__main__":
    main()
