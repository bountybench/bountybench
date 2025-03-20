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

from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.phase_messages.phase_message import PhaseMessage
from workflows.base_workflow import BaseWorkflow
from workflows.detect_patch_workflow import DetectPatchWorkflow
from workflows.exploit_patch_workflow import ExploitPatchWorkflow
from workflows.patch_workflow import PatchWorkflow

# This module serves as the single entry point for running workflows via the command line.
# Example usage:
# python -m workflows.runner --workflow-type exploit_patch_workflow \
#     --task_dir bountybench/lunary \
#     --bounty_number 0 \
#     --model anthropic/claude-3-5-sonnet-20240620 \
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
    }

    def __init__(self):
        self.parser = self._create_parser()
        self.args = None
        self.workflow = None
        self.kwargs = {}
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
            "--interactive", action="store_true", help="Enable interactive mode"
        )
        parser.add_argument(
            "--continue_from_log",
            type=str,
            help="Path to a log file to continue a workflow from",
        )
        parser.add_argument(
            "--additional_iterations",
            type=int,
            default=1,
            help="Number of additional iterations to run when continuing from a log",
        )

        return parser

    def parse_arguments(self) -> None:
        self.args = self.parser.parse_args()

    def initialize_workflow(self) -> None:
        """Initialize the workflow instance with parsed arguments or load from log."""

        if self.args.continue_from_log:
            # Load workflow from log
            self.workflow = self._load_workflow_from_log(self.args.continue_from_log)

            self.kwargs = {
                "continue_from_log": self.args.continue_from_log,
                "additional_iterations": self.args.additional_iterations,
            }

            # Set the additional iterations in the workflow params
            if not hasattr(self.workflow, "params"):
                self.workflow.params = {}
            self.workflow.params["phase_iterations"] = self.args.additional_iterations
        else:
            # Standard initialization
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

            # If we're continuing from a log, we need to run differently
            if self.args.continue_from_log:
                # Set up the current phase
                if self.workflow._current_phase:
                    await self.workflow.run_restart()
                else:
                    console.print("[bold yellow]No more phases to run.[/]")
            else:
                # Normal run
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

    @staticmethod
    def load_message_tree(workflow_message, log_data):
        """
        Reconstruct message tree from log data without broadcasting updates
        during the construction phase
        """
        # Store original broadcast function
        from messages.message_utils import broadcast_update

        original_broadcast = broadcast_update

        # Temporarily disable broadcasting
        from messages.message_utils import broadcast_update

        def no_op_broadcast(*args, **kwargs):
            pass

        # Replace broadcast function
        import messages.message_utils

        messages.message_utils.broadcast_update = no_op_broadcast

        try:
            workflow_id = workflow_message.workflow_id

            # Create message ID to object mapping for resolving relationships
            id_map = {workflow_message.id: workflow_message}

            # Load phase messages
            for phase_data in log_data.get("phase_messages", []):
                phase_message = PhaseMessage.from_dict(phase_data)
                # Don't use add_child_message here to avoid broadcasting
                workflow_message._phase_messages.append(phase_message)
                phase_message._parent = workflow_message
                id_map[phase_message.id] = phase_message

                # Load agent messages for this phase
                for agent_data in phase_data.get("agent_messages", []) or []:
                    agent_message = AgentMessage.from_dict(agent_data)
                    # Don't use add_child_message here to avoid broadcasting
                    phase_message._agent_messages.append(agent_message)
                    agent_message._parent = phase_message
                    id_map[agent_message.id] = agent_message

                    # Load action messages for this agent
                    for action_data in agent_data.get("action_messages", []) or []:
                        action_message = ActionMessage.from_dict(action_data)
                        # Don't use add_child_message here to avoid broadcasting
                        agent_message._action_messages.append(action_message)
                        action_message._parent = agent_message
                        id_map[action_message.id] = action_message

            # Now resolve prev/next relationships
            for message_id, message in id_map.items():
                # Resolve prev relationship if it's an ID string
                if hasattr(message, "_prev") and isinstance(message._prev, str):
                    if message._prev in id_map:
                        message._prev = id_map[message._prev]
                    else:
                        message._prev = None  # Clear dangling references

                # Resolve next relationship if it's an ID string
                if hasattr(message, "_next") and isinstance(message._next, str):
                    if message._next in id_map:
                        message._next = id_map[message._next]
                    else:
                        message._next = None  # Clear dangling references

            # Set up message dictionary for future operations
            from messages.message_utils import message_dict

            if workflow_id not in message_dict:
                message_dict[workflow_id] = {}

            # Add all constructed messages to the dictionary
            for msg_id, msg in id_map.items():
                message_dict[workflow_id][msg_id] = msg

            return workflow_message

        finally:
            # Restore original broadcast function
            messages.message_utils.broadcast_update = original_broadcast

    def _replay_commands(self, workflow, log_data):
        """Replay all commands from the log to restore environment state."""
        import subprocess

        console.print(f"[yellow]Extracting commands from log...[/]")

        # Extract all commands from the log
        commands = []
        for phase_data in log_data.get("phase_messages", []):
            for agent_data in phase_data.get("agent_messages", []) or []:
                for action_data in agent_data.get("action_messages", []) or []:
                    if "command" in action_data:
                        commands.append(action_data["command"])

        console.print(f"[yellow]Found {len(commands)} commands to replay[/]")

        # Ensure the phase is set up
        if workflow._current_phase:
            console.print(
                f"[yellow]Setting up phase {workflow._current_phase.name}...[/]"
            )
            workflow._current_phase.setup()

        # Re-run all commands to restore environment state
        for i, command in enumerate(commands):
            console.print(
                f"[yellow]Replaying command {i+1}/{len(commands)}: {command}[/]"
            )

            # Skip invalid or empty commands
            if not command or command.strip() == "":
                continue

            try:
                # Use the resource manager to get the Kali environment
                kali_env_resource = None
                for (
                    resource_id,
                    resource,
                ) in workflow.resource_manager._resources.id_to_resource.get(
                    workflow.workflow_message.workflow_id, {}
                ).items():
                    if "kali_env" in resource_id:
                        kali_env_resource = resource
                        break

                if kali_env_resource:
                    # Execute command in the kali environment
                    result = kali_env_resource.execute_command(command)
                    console.print(
                        f"[dim]{result[:100]}...[/]"
                        if len(result) > 100
                        else f"[dim]{result}[/]"
                    )
                else:
                    # Fallback to subprocess
                    result = subprocess.run(
                        command, shell=True, capture_output=True, text=True, check=False
                    )
                    console.print(
                        f"[dim]{result.stdout[:100]}...[/]"
                        if len(result.stdout) > 100
                        else f"[dim]{result.stdout}[/]"
                    )
            except Exception as e:
                console.print(f"[red]Error replaying command: {e}[/]")
                # Continue with next command even if this one failed

        console.print(f"[green]Finished replaying commands[/]")

    def _load_workflow_from_log(self, log_path: str) -> BaseWorkflow:
        """Load a workflow from a log file."""
        import json
        from pathlib import Path

        log_path = Path(log_path)
        if not log_path.exists():
            raise ValueError(f"Log file does not exist: {log_path}")

        with open(log_path, "r") as f:
            log_data = json.load(f)

        # Get workflow type from log data
        workflow_name = log_data.get("workflow_metadata", {}).get("workflow_name")
        if not workflow_name:
            raise ValueError(f"No workflow name found in log file")

        # Convert class name (PascalCase) to workflow type (snake_case)
        workflow_type = "".join(
            ["_" + c.lower() if c.isupper() else c for c in workflow_name]
        ).lstrip("_")

        if workflow_type not in self._workflow_factory:
            raise ValueError(
                f"Unknown workflow type in log: {workflow_name} (converted to {workflow_type})"
            )

        workflow_class = self._workflow_factory[workflow_type]

        # Extract task parameters from the log
        task = log_data.get("workflow_metadata", {}).get("task", {})
        bounty_number = task.get("bounty_number")
        task_dir = task.get("task_dir")

        # Get the model and other config from resources_used
        resources = log_data.get("resources_used", {})
        model_resource = resources.get("model", {})
        model_config = model_resource.get("config", {})

        # Prepare kwargs for workflow instantiation
        kwargs = {
            "task_dir": Path(task_dir) if task_dir else None,
            "bounty_number": bounty_number,
            "model": model_config.get("model"),
            "use_helm": model_config.get("helm", False),
            "use_mock_model": model_config.get("use_mock_model", False),
            "max_input_tokens": model_config.get("max_input_tokens"),
            "max_output_tokens": model_config.get("max_output_tokens"),
            "phase_iterations": self.args.additional_iterations,  # New iterations count
        }

        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # Create workflow instance with extracted parameters
        workflow = workflow_class(**kwargs)

        # Load workflow state from log
        from messages.workflow_message import WorkflowMessage

        workflow_message = WorkflowMessage.from_dict(log_data)

        # Load the message tree
        workflow.workflow_message = self.load_message_tree(workflow_message, log_data)

        # Set the current phase to be the last one that ran
        phase_messages = workflow.workflow_message.phase_messages
        if phase_messages:
            last_phase = phase_messages[-1]
            console.print(f"[green]Last phase was: {last_phase.phase_id}[/]")

            # Find the phase in the workflow's phase graph
            for phase in workflow._phase_graph:
                if phase.name == last_phase.phase_id:
                    workflow._current_phase = phase
                    console.print(f"[green]Setting current phase to: {phase.name}[/]")

                    # Now setup the phase - this will initialize resources
                    workflow._setup_phase(phase)

                    # At this point resources should be initialized
                    # We can now attempt to access and configure the memory resource
                    try:
                        memory_resource = workflow.resource_manager.get_resource(
                            "executor_agent_memory"
                        )

                        # Pin key messages from the previous session
                        for phase_data in log_data.get("phase_messages", []):
                            for agent_data in (
                                phase_data.get("agent_messages", []) or []
                            ):
                                # System messages are particularly important
                                if agent_data.get(
                                    "agent_id"
                                ) == "system" and agent_data.get("message"):
                                    memory_resource.pin(
                                        f"[system] {agent_data['message']}"
                                    )

                                # Also pin command outputs that had results
                                for action_data in (
                                    agent_data.get("action_messages", []) or []
                                ):
                                    if "command" in action_data and action_data.get(
                                        "message"
                                    ):
                                        agent_id = agent_data.get("agent_id", "")
                                        resource_id = action_data.get("resource_id", "")
                                        message_str = f"[{agent_id}/{resource_id}] {action_data.get('message', '')}"
                                        memory_resource.pin(message_str)
                    except KeyError:
                        # If memory resource isn't available yet, that's okay - the phase setup will initialize it
                        console.print(
                            "[yellow]Memory resource not initialized yet, will be set up during phase run[/]"
                        )

                    break

            # Set up and run all the commands from the log to restore the environment state
            console.print(
                f"[yellow]Replaying commands to restore environment state...[/]"
            )
            self._replay_commands(workflow, log_data)

            # If the last phase was successful, set the current phase to the next phase
            if last_phase.success:
                next_phases = workflow._phase_graph.get(workflow._current_phase, [])
                if next_phases:
                    workflow._current_phase = next_phases[0]
                    console.print(
                        f"[green]Last phase was successful, moving to next phase: {workflow._current_phase.name}[/]"
                    )

        return workflow


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
