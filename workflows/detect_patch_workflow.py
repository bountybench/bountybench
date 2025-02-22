import asyncio
from pathlib import Path

from prompts.prompts import DETECT_PATCH_PROMPT, TARGET_HOST_DETECT_PATCH_PROMPT
from utils.logger import get_main_logger
from workflows.patch_workflow import PatchWorkflow

logger = get_main_logger(__name__)


class DetectPatchWorkflow(PatchWorkflow):
    """Workflow for detecting vulnerabilities"""

    def __init__(self, *args, **kwargs):
        kwargs["use_agent_exploit"] = True
        super().__init__(*args, **kwargs)

    """Workflow for detecting vulnerabilities"""

    def _get_initial_prompt(self):
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """
        return (
            TARGET_HOST_DETECT_PATCH_PROMPT
            if self.repo_metadata["target_host"]
            else DETECT_PATCH_PROMPT
        )


async def main() -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run the exploit and patch workflow")
    parser.add_argument("--task_dir", type=str, required=True, help="The directory of the task repo")
    parser.add_argument("--bounty_number", type=str, required=True, help="The bounty number")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--use_mock_model", action="store_true", help="Use mock model")
    parser.add_argument(
        "--task_dir", type=str, required=True, help="The directory of the task repo"
    )
    parser.add_argument(
        "--bounty_number", type=str, required=True, help="The bounty number"
    )
    parser.add_argument(
        "--vulnerability_type", type=str, help="The vulnerability type for detection"
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
    workflow = DetectPatchWorkflow(
        task_dir=Path(args.task_dir),
        bounty_number=args.bounty_number,
        vulnerability_type=args.vulnerability_type,
        interactive=args.interactive,
        use_mock_model=args.use_mock_model,
        model=args.model,
        phase_iterations=args.phase_iterations,
    )
    await workflow.run()


if __name__ == "__main__":
    asyncio.run(main())
