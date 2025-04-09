import argparse
import asyncio
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Type

from rich.console import Console
from rich.traceback import Traceback

from utils.logger import get_main_logger, logger_config
from workflows.base_workflow import BaseWorkflow
from workflows.detect_patch_workflow import DetectPatchWorkflow
from workflows.exploit_patch_workflow import ExploitPatchWorkflow
from workflows.exploit_workflow import ExploitWorkflow
from workflows.patch_workflow import PatchWorkflow
from workflows.detect_workflow import DetectWorkflow

# This module serves as the single entry point for running workflows via the command line.
# Example usage:
# python -m workflows.runner --workflow-type exploit_patch_workflow \
#     --task_dir bountybench/lunary \
#     --bounty_number 0 \
#     --model anthropic/claude-3-5-sonnet-20241022 \
#     --phase_iterations 1 \
#     --use_helm


console = Console(record=True)

import signal


def signal_handler(signum, frame):
    console.print(f"[bold red]Received signal {signum}. Exiting with error.[/]")
    sys.exit(1)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


class WorkflowRunner:
    """Centralized workflow runner with error handling and dynamic argument parsing."""

    _workflow_factory: Dict[str, Type[BaseWorkflow]] = {
        "exploit_patch_workflow": ExploitPatchWorkflow,
        "detect_patch_workflow": DetectPatchWorkflow,
        "patch_workflow": PatchWorkflow,
        "detect_workflow": DetectWorkflow,
        "exploit_workflow": ExploitWorkflow,
    }

    def __init__(self):
        self.parser = self._create_parser()
        self.args = None
        self.workflow = None
        self.kwargs = None
        self.error_log_dir = Path("error_logs")

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Run security testing workflows")
        parser.add_argument(
            "--workflow-type",
            type=str,
            required=True,
            choices=list(self._workflow_factory.keys()),
            help="Type of workflow to execute",
        )
        parser.add_argument(
            "--task_dir", type=str, help="Path to the task repository directory"
        )
        parser.add_argument("--bounty_number", type=str, help="Bounty number to target")
        parser.add_argument(
            "--vulnerability_type",
            type=str,
            help="Vulnerability type to detect (for detect_patch_workflow)",
        )
        parser.add_argument(
            "--phase_iterations",
            type=int,
            help="Maximum iterations for workflow phases",
        )
        parser.add_argument(
            "--use_mock_model", action="store_true", help="Use a mock model for testing"
        )
        parser.add_argument("--use_helm", action="store_true", help="Use HelmModels")
        parser.add_argument("--model", type=str, help="LM model to query")
        parser.add_argument(
            "--max_input_tokens", type=int, help="Maximum tokens to pass to the model"
        )
        parser.add_argument(
            "--max_output_tokens", type=int, help="Maximum tokens for model output"
        )
        parser.add_argument(
            "--no_submit", action="store_false", help="Disable agent from submitting the exploit"
        )

        return parser

    def parse_arguments(self) -> None:
        self.args = self.parser.parse_args()

    def initialize_workflow(self) -> None:
        """Initialize the workflow instance with parsed arguments."""
        workflow_class = self._workflow_factory[self.args.workflow_type]

        # Convert parsed args to kwargs
        kwargs = vars(self.args).copy()
        # Remove workflow-type as it's not needed for workflow instantiation
        kwargs.pop("workflow_type")

        # Remove None values from kwargs
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # Handle path conversions
        for arg in ["task_dir", "log_dir"]:
            if arg in kwargs and kwargs[arg] is not None:
                kwargs[arg] = Path(kwargs[arg])

        self.kwargs = kwargs
        self.workflow = workflow_class(**kwargs)

    async def run(self) -> int:
        """Execute the workflow with error handling."""
        try:
            console.print(f"[bold green]*" * 40)
            console.print(
                f"[bold green]Starting {self.args.workflow_type} workflow...[/]"
            )
            console.print(f"[bold green]*" * 40)
            await self.workflow.run()

            # Check if the workflow is complete
            if not self.check_workflow_completion():
                raise Exception("Workflow marked as incomplete in the log file.")

            console.print(f"[bold green]*" * 40)
            console.print(
                f"[bold green]Completed {self.args.workflow_type} workflow[/]"
            )
            console.print(f"[bold green]*" * 40)
            return 0
        except Exception as e:
            console.print(f"[bold red]*" * 40)
            console.print(
                f"[bold red]Error in {self.args.workflow_type} workflow:[/] {e}"
            )
            console.print(f"[bold red]*" * 40)
            console.print(Traceback())

            # Create error report
            self.create_error_report(e)

            sys.exit(1)

    def check_workflow_completion(self) -> bool:
        """Check if the workflow is marked as complete in the log file."""
        try:
            log_file_path = Path(self.workflow.workflow_message.log_file)
            if not log_file_path.exists():
                console.print(
                    f"[bold yellow]Warning: Log file not found: {log_file_path}[/]"
                )
                return False

            with log_file_path.open("r") as log_file:
                log_data = json.load(log_file)
                workflow_complete = (
                    log_data.get("workflow_metadata", {})
                    .get("workflow_summary", {})
                    .get("complete", False)
                )
                if not workflow_complete:
                    console.print(
                        "[bold red]Workflow marked as incomplete in the log file.[/]"
                    )
                    return False
                return True
        except Exception as e:
            console.print(f"[bold red]Error checking workflow completion: {e}[/]")
            return False

    def create_error_report(self, error: Exception) -> None:
        """Create an error report file with the error details and console output."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create error log directory if it doesn't exist
        self.error_log_dir.mkdir(exist_ok=True, parents=True)

        error_file = self.error_log_dir / f"error_report_{timestamp}.txt"

        log_file = None
        if (
            self.workflow
            and hasattr(self.workflow, "workflow_message")
            and hasattr(self.workflow.workflow_message, "log_file")
        ):
            log_file = Path(self.workflow.workflow_message.log_file)

        with error_file.open("w") as f:
            f.write("ERROR REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Workflow Type: {self.args.workflow_type}\n")
            f.write(f"Timestamp: {timestamp}\n")
            if log_file:
                f.write(f"Log File: {log_file}\n")
            f.write("\n")

            f.write("Workflow Arguments:\n")
            f.write("-" * 50 + "\n")
            for key, value in self.kwargs.items():
                f.write(f"{key}: {str(value)}\n")
            f.write("\n")

            f.write("Error Details:\n")
            f.write("-" * 50 + "\n")
            f.write(f"{error.__class__.__name__}: {str(error)}\n\n")
            f.write("Traceback:\n")
            f.write(traceback.format_exc())
            f.write("\n" + "=" * 50 + "\n\n")

            # Include recent logs from the buffer
            f.write("Recent Logs:\n")
            f.write("-" * 50 + "\n")
            for log_entry in logger_config.log_buffer_handler.get_logs():
                f.write(log_entry + "\n")
            f.write("=" * 50 + "\n\n")  # End of highlighted section

            if log_file:
                f.write("Workflow Log File:\n")
                f.write("-" * 50 + "\n")
                log_file_path = Path(self.workflow.workflow_message.log_file)
                if log_file_path.exists():
                    with log_file_path.open("r") as log_file:
                        f.write(log_file.read())
                else:
                    f.write(f"Log file not found: {log_file_path}\n")
                f.write("\n" + "=" * 50 + "\n\n")

            f.write("Console Output:\n")
            f.write("-" * 50 + "\n")
            f.write(console.export_text())

        console.print(f"[bold yellow]Error report created: {error_file}[/]")


async def main() -> int:
    """Main entry point for workflow execution."""
    runner = WorkflowRunner()
    try:
        runner.parse_arguments()
        runner.initialize_workflow()
        return await runner.run()
    except Exception as e:
        console.print(f"[bold red]Initialization error:[/] {e}")
        console.print(Traceback())
        runner.create_error_report(e)
        sys.exit(1)
    except SystemExit:
        raise


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
