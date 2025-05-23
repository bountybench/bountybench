import argparse
import asyncio
import itertools
import os
import platform
import shlex
import shutil
import sys
import time
from collections import defaultdict
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

import yaml
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.table import Table


class ExperimentRunner:
    def __init__(self, config_path: str, hold_terminals: bool = False):
        self.config = self._load_config(config_path)
        self.os_type = platform.system()
        self.hold_terminals = hold_terminals
        self.terminal_handlers = {
            "Darwin": self._run_macos,
            "Linux": self._run_linux,
            "Windows": self._run_windows,
        }
        self.console = Console()
        self.task_status = {}
        self.task_start_times = {}

    def _load_config(self, path: str) -> Dict:
        with open(path) as f:
            return yaml.safe_load(f)

    def generate_commands(self) -> List[Tuple[int, List[str]]]:
        """Generate commands for all experiment combinations using itertools.product"""
        commands = []
        task_id = 0

        # Extract common parameters
        workflow_type = self.config["workflow_type"]
        trials_per_config = self.config.get("trials_per_config", 1)

        # Extract and normalize parameters
        tasks = self.config.get("tasks", [])
        models = self.config.get("models", [])
        phase_iterations = self._ensure_list(self.config.get("phase_iterations", [1]))
        vulnerability_types = self._ensure_list(
            self.config.get("vulnerability_type", [])
        )
        mock_model = self.config.get("use_mock_model", False)
        # Prepare parameters for itertools.product
        params = [tasks, models, phase_iterations]

        # Only include vulnerability_types if it's non-empty and workflow is detect_
        if vulnerability_types and workflow_type.startswith("detect_"):
            params.append(vulnerability_types)

        # Generate all combinations of parameters
        for combination in itertools.product(*params):
            task, model, iterations = combination[:3]
            vuln_type = combination[3] if len(combination) > 3 else None

            for _ in range(trials_per_config):
                cmd = self._build_command(
                    workflow_type,
                    task["task_dir"],
                    task["bounty_number"],
                    model["name"],
                    model.get("helm", False),
                    mock_model,
                    iterations,
                    vuln_type,
                )
                commands.append((task_id, cmd))
                task_id += 1

        return commands

    def _ensure_list(self, value):
        """Ensure the input is a list (convert single values to a single-item list)"""
        return value if isinstance(value, list) else [value]

    def _build_command(
        self,
        workflow_type: str,
        task_dir: str,
        bounty_number: str,
        model_name: str,
        use_helm: bool,
        use_mock_model: bool,
        phase_iterations: int,
        vulnerability_type: Optional[str] = "",
    ) -> List[str]:
        """Build a command for the workflow runner"""
        cmd = [
            sys.executable,
            "-m",
            "workflows.runner",
            "--workflow-type",
            workflow_type,
            "--task_dir",
            task_dir,
            "--bounty_number",
            bounty_number,
            "--model",
            model_name,
            "--phase_iterations",
            str(phase_iterations),
        ]

        if use_helm:
            cmd.append("--use_helm")
        if use_mock_model:
            cmd.append("--use_mock_model")
        if vulnerability_type and workflow_type.startswith("detect_"):
            cmd.extend(["--vulnerability_type", vulnerability_type])

        return cmd

    async def _run_macos(self, command: List[str]):
        """Run command in new macOS Terminal window"""
        # Get the current working directory
        current_dir = os.getcwd()

        # Method 1: Use a temporary file to track completion
        import tempfile

        # Create a unique marker file
        marker_file = tempfile.mktemp(suffix=".done")

        # Modify the command to touch the marker file when done
        cmd_str = " ".join(shlex.quote(arg) for arg in command)
        full_cmd = f"cd {shlex.quote(current_dir)} && {cmd_str}; RESULT=$?; touch {marker_file}; exit $RESULT"

        mac_script = f"""
        tell application "Terminal"
            activate
            do script "{full_cmd}"
        end tell
        """

        # Launch the terminal
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", mac_script.strip()
        )

        # Wait for the osascript to complete (launches Terminal)
        await proc.wait()

        # Now wait for the marker file to appear
        while not os.path.exists(marker_file):
            await asyncio.sleep(1)

        # Clean up marker file
        try:
            os.remove(marker_file)
        except:
            pass

        # Return 0 to indicate success
        return proc

    async def _run_windows(self, command: List[str]):
        """Run command in new Windows cmd window"""
        return await asyncio.create_subprocess_exec(
            "start",
            "cmd",
            "/k" if not self.hold_terminals else "/c",
            *command,
            shell=True,
        )

    async def _run_linux(self, command: List[str]):
        """Run command in a terminal in Linux"""
        cmd_str = " ".join(shlex.quote(arg) for arg in command)

        # Handle the various terminal options
        if self.hold_terminals:
            terminals = [
                ("xterm", ["-fa", "Monospace", "-fs", "12", "-e"]),
                ("xfce4-terminal", ["--disable-server", "--command"]),
                ("mate-terminal", ["--disable-factory", "-e"]),
                ("lxterminal", ["--command"]),
                ("konsole", ["-e"]),
            ]
        else:
            terminals = [
                ("xterm", ["-fa", "Monospace", "-fs", "12", "-hold", "-e"]),
                ("xfce4-terminal", ["--disable-server", "--command"]),
                ("mate-terminal", ["--disable-factory", "-x"]),
                ("lxterminal", ["--command"]),
                ("konsole", ["--hold", "-e"]),
            ]

        for terminal, args in terminals:
            if not shutil.which(terminal):
                continue

            try:
                proc = await asyncio.create_subprocess_exec(
                    terminal,
                    *args,
                    cmd_str,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                # Return here since we just start the command Execution
                return proc
            except Exception as e:
                continue

        # Fallback if no terminal emulator found
        return await self._run_fallback(cmd_str)

    async def _run_fallback(self, cmd_str: str):
        """Final fallback with error suppression"""
        try:
            return await asyncio.create_subprocess_exec(
                "xterm",
                "-fa",
                "DejaVu Sans Mono",  # Widely available font
                "-fs",
                "12",
                "-hold -e" if self.hold_terminals else "-e",
                cmd_str,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except Exception:
            return await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

    def _get_task_dir_from_command(self, command: List[str]) -> str:
        """Extract task_dir from command arguments"""
        try:
            task_dir_index = command.index("--task_dir") + 1
            return command[task_dir_index]
        except ValueError:
            return "default"

    def _get_bounty_from_command(self, command: List[str]) -> str:
        """Extract bounty number from command arguments"""
        try:
            bounty_index = command.index("--bounty_number") + 1
            return command[bounty_index]
        except ValueError:
            return "unknown"

    def _get_ports(self, task_dir):
        from utils.get_task_ports import get_ports_for_directory

        return get_ports_for_directory(task_dir)

    def task_groups_port_constraints(self, task_groups):
        """
        Note that this grouping logic does a single pass grouping, does not handle
        mixed conflict grouping (e.g. [8000], [9000], [8000, 9000] would result in
        two groups assuming [8000, 9000] isn't evaluated first/second - since conflict
        won't be known between [8000] and [9000]). However, this is still likely
        sufficient for our purposes based on current bounties.
        """

        port_map = {}
        new_task_groups = defaultdict(list)

        for task_dir, cmds in task_groups.items():
            ports = self._get_ports(task_dir)
            conflicting_group = None
            for port in ports:
                if port in port_map:
                    conflicting_group = port_map[port]
                    break

            group_key = conflicting_group
            if conflicting_group:
                new_task_groups[conflicting_group].extend(cmds)
            else:
                group_key = f"group_{len(new_task_groups)}"
                new_task_groups[group_key].extend(cmds)

            for port in ports:
                port_map[port] = group_key

        return dict(new_task_groups)

    async def run_all(self):
        commands = self.generate_commands()
        total_tasks = len(commands)

        # Initialize task status
        for task_id, cmd in commands:
            self.task_status[task_id] = {
                "status": "Waiting",
                "task_dir": self._get_task_dir_from_command(cmd),
                "bounty": self._get_bounty_from_command(cmd),
                "command": " ".join(cmd),
            }

        # Group commands by task_dir
        task_groups = defaultdict(list)
        for task_id, cmd in commands:
            task_dir = self._get_task_dir_from_command(cmd)
            task_groups[task_dir].append((task_id, cmd))

        task_groups = self.task_groups_port_constraints(task_groups)

        # Set up progress
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        overall_task = progress.add_task("[cyan]Overall Progress", total=total_tasks)

        async def run_task_group(cmds):
            return await self.run_task_dir(cmds, progress, overall_task)

        display_group = Group(
            Panel(progress),
            Panel(self.generate_status_table(), title="Experiment Status"),
        )

        all_results = []
        with Live(display_group, refresh_per_second=4) as live:
            tasks = [
                asyncio.create_task(run_task_group(cmds))
                for task_dir, cmds in task_groups.items()
            ]

            while tasks:
                done, tasks = await asyncio.wait(
                    tasks, timeout=0.5, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    all_results.extend(task.result())
                live.update(Group(progress, self.generate_status_table()))

            # Ensure we catch the final state
            await asyncio.sleep(0.5)
            live.update(Group(progress, self.generate_status_table()))

        self.console.print("\nExperiment Summary:")
        success_count = sum(1 for result in all_results if result == 0)
        self.console.print(
            f"Successfully completed {success_count}/{total_tasks} experiments"
        )
        self.console.print(f"Failed: {total_tasks - success_count}")

    async def run_task_dir(
        self,
        commands: List[Tuple[int, List[str]]],
        progress: Progress,
        overall_task,
    ):
        """Run commands for a task_dir with proper sequencing and status updates"""
        results = []
        for task_id, cmd in commands:
            self.task_status[task_id]["status"] = "Running"
            self.task_start_times[task_id] = time.time()
            result = await self.run_experiment(cmd)
            end_time = time.time()
            elapsed_time = end_time - self.task_start_times[task_id]
            self.task_status[task_id]["status"] = (
                "Completed" if result == 0 else "Failed"
            )
            self.task_status[task_id]["elapsed_time"] = elapsed_time
            results.append(result)
            progress.update(overall_task, advance=1)

        return results

    async def run_experiment(self, command: List[str]):
        """Run a single experiment and wait for completion"""
        try:
            handler = self.terminal_handlers.get(self.os_type)
            if not handler:
                raise NotImplementedError(f"Unsupported OS: {self.os_type}")

            proc = await handler(command)
            return_code = await proc.wait()
            return return_code
        except Exception as e:
            self.console.print(f"Failed to launch experiment: {e}", style="bold red")
            return 1

    def generate_status_table(self) -> Table:
        """Generate a rich Table with current task status"""
        table = Table(title="Experiment Status", expand=True)
        table.add_column("ID")
        table.add_column("Task Dir")
        table.add_column("Bounty")
        table.add_column("Status")
        table.add_column("Time Elapsed")
        table.add_column("Command")

        status_styles = {
            "Completed": Style(color="magenta"),
            "Failed": Style(color="red"),
            "Running": Style(color="green"),
            "Waiting": Style(color="yellow"),
            "Pending": Style(color="white"),  # Default color for any other status
        }

        current_time = time.time()

        def format_elapsed_time(seconds):
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}"

        for task_id, task_info in self.task_status.items():
            full_command = task_info["command"]
            workflows_index = full_command.index("workflows.")
            truncated_command = full_command[workflows_index:]

            # Remove task_dir and bounty_number from the command
            command_parts = truncated_command.split()
            simplified_command = [
                part
                for i, part in enumerate(command_parts)
                if part not in ["--task_dir", "--bounty_number"]
                and i > 0
                and command_parts[i - 1] not in ["--task_dir", "--bounty_number"]
            ]
            simplified_command = " ".join(simplified_command)

            status = task_info["status"]
            row_style = status_styles.get(status, Style(color="white"))

            # Calculate elapsed time
            if status == "Running":
                elapsed_time = current_time - self.task_start_times.get(
                    task_id, current_time
                )
            elif status in ["Completed", "Failed"]:
                elapsed_time = task_info.get("elapsed_time", 0)
            else:
                elapsed_time = 0

            elapsed_str = format_elapsed_time(elapsed_time)

            table.add_row(
                str(task_id),
                task_info["task_dir"],
                task_info["bounty"],
                status,
                elapsed_str,
                simplified_command,
                style=row_style,
            )

        return table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experiment Runner")
    parser.add_argument("config", help="Path to YAML config file")
    parser.add_argument(
        "--hold-terminals",
        action="store_false",
        help="Keep terminals open after completion",
    )
    args = parser.parse_args()

    runner = ExperimentRunner(args.config, args.hold_terminals)

    asyncio.run(runner.run_all())
