import asyncio
from pathlib import Path

from agents.prompts import DETECT_PROMPT, STOP_TOKEN, TARGET_HOST_DETECT_PROMPT
from phases.exploit_phase import ExploitPhase
from resources.utils import read_writeup
from utils.logger import get_main_logger
from workflows.bounty_workflow import BountyWorkflow

logger = get_main_logger(__name__)


class DetectWorkflow(BountyWorkflow):
    """Workflow for detecting vulnerabilities"""

    def _create_phases(self):
        """Define and create phases specific to DetectWorkflow."""

        phase_kwargs = {
            "model": self.params.get("model"),
            "helm": self.params.get("helm"),
            "task_dir": self.task_dir,
            "bounty_number": self.bounty_number,
            "target_host": self.repo_metadata["target_host"],
            "stop_token": STOP_TOKEN,
            "initial_prompt": self.initial_prompt,
        }
        if hasattr(self, "phase_iterations"):
            phase_kwargs["max_iterations"] = self.phase_iterations

        phase_kwargs["interactive"] = self.interactive

        exploit_phase = ExploitPhase(workflow=self, **phase_kwargs)

        self._register_root_phase(exploit_phase)

    def _get_initial_prompt(self):
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """
        return (
            TARGET_HOST_DETECT_PROMPT
            if self.repo_metadata["target_host"]
            else DETECT_PROMPT
        )


async def main() -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run the exploit and patch workflow")
    parser.add_argument(
        "--task_dir", type=str, required=True, help="The directory of the task repo"
    )
    parser.add_argument(
        "--bounty_number", type=str, required=True, help="The bounty number"
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument("--model", type=str, help="The LM model to query")
    parser.add_argument("--helm", action="store_true", help="Use HelmModels")
    parser.add_argument(
        "--phase_iterations",
        type=int,
        help="max iteractions to run of ExploitPhase and PatchPhase each",
    )

    args = parser.parse_args()

    logger.info("Parsed command line args")

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logger.info(f"Created logs directory at: {logs_dir}")

    # Run workflow
    workflow = DetectWorkflow(
        task_dir=Path(args.task_dir),
        bounty_number=args.bounty_number,
        interactive=args.interactive,
        model=args.model,
        phase_iterations=args.phase_iterations,
    )
    await workflow.run()


if __name__ == "__main__":
    asyncio.run(main())
