import asyncio
from pathlib import Path

from phases.patch_phase import PatchPhase
from prompts.prompts import PATCH_PROMPT, STOP_TOKEN, TARGET_HOST_PATCH_PROMPT
from resources.utils import read_writeup
from utils.logger import get_main_logger
from workflows.bounty_workflow import BountyWorkflow

logger = get_main_logger(__name__)


class PatchWorkflow(BountyWorkflow):
    """Workflow for patching vulnerabilities"""

    def __init__(self, *args, **kwargs):
        self._use_agent_exploit = kwargs.pop("use_agent_exploit", False)
        super().__init__(*args, **kwargs)

    @property
    def use_agent_exploit(self):
        return self._use_agent_exploit

    def _create_phases(self):
        """Define and register phases specific to PatchWorkflow."""

        phase_kwargs = {
            "use_mock_model": self.params.get("use_mock_model"),
            "model": self.params.get("model"),
            "helm": self.params.get("use_helm"),
            "task_dir": self.task_dir,
            "bounty_number": self.bounty_number,
            "vulnerability_type": self.params.get("vulnerability_type"),
            "max_iterations": 20,
            "use_agent_exploit": self.use_agent_exploit,
            "task_description": read_writeup(self.task_dir, self.bounty_number),
            "stop_token": STOP_TOKEN,
            "target_host": self.repo_metadata["target_host"],
            "initial_prompt": self.initial_prompt,
            "info": self.repo_metadata.get("info", "")
            + "\n"
            + self.bounty_metadata.get("info", ""),
            "max_input_tokens": self.params.get("max_input_tokens"),
            "max_output_tokens": self.params.get("max_output_tokens"),
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
        return (
            TARGET_HOST_PATCH_PROMPT
            if self.repo_metadata["target_host"]
            else PATCH_PROMPT
        )


async def main() -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run the patch workflow")
    parser.add_argument(
        "--task_dir", type=str, help="The directory of the task repo", required=True
    )
    parser.add_argument(
        "--bounty_number", type=str, help="The bounty number", required=True
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Enable interactive mode"
    )
    parser.add_argument("--use_mock_model", action="store_true", help="Use mock model")
    parser.add_argument("--model", type=str, help="The LM model to query")
    parser.add_argument("--helm", action="store_true", help="Use HelmModels")
    parser.add_argument(
        "--max_input_tokens", type=int, help="Max input tokens to pass into model"
    )
    parser.add_argument(
        "--max_output_tokens", type=int, help="Max output tokens to pass into model"
    )
    parser.add_argument(
        "--phase_iterations", type=int, help="max iteractions to run of PatchPhase"
    )
    args = parser.parse_args()

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Run workflow
    workflow = PatchWorkflow(
        task_dir=Path(args.task_dir),
        bounty_number=args.bounty_number,
        interactive=args.interactive,
        use_mock_model=args.use_mock_model,
        model=args.model,
        max_input_tokens=args.max_input_tokens,
        max_output_tokens=args.max_output_tokens,
        phase_iterations=args.phase_iterations,
    )
    await workflow.run()


if __name__ == "__main__":
    asyncio.run(main())
