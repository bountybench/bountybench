import argparse
import asyncio
import itertools
import os
import platform
import shlex
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from time import sleep
from typing import Dict, List, Optional

import yaml


class ExperimentRunner:
    def __init__(self, config_path: str, close_terminals: bool = False):
        self.config = self._load_config(config_path)
        self.os_type = platform.system()
        self.close_terminals = close_terminals
        self.terminal_handlers = {
            "Darwin": self._run_macos,
            "Linux": self._run_linux,
            "Windows": self._run_windows,
        }

    def _load_config(self, path: str) -> Dict:
        with open(path) as f:
            return yaml.safe_load(f)

    def _build_base_command(self, model: str, use_helm: bool) -> List[str]:
        """Construct the core workflow command with parameters"""
        cmd = [
            sys.executable,
            "-m",
            f"workflows.{self.config['workflow_type']}",
            "--model",
            model,
        ]

        if use_helm:
            cmd.append("--helm")

        # Add static parameters
        for key, value in self.config.items():
            if key in [
                "workflow_type",
                "repetitions",
                "helm_models",
                "non_helm_models",
            ]:
                continue
            if not isinstance(value, list):
                cmd.extend([f"--{key}", str(value)])

        return cmd

    def generate_commands(self) -> List[List[str]]:
        """Generate commands for all experiment combinations using itertools.product"""
        commands = []

        # Extract common parameters
        workflow_type = self.config["workflow_type"]
        repetitions = self.config.get("repetitions", 1)

        # Extract and normalize parameters
        tasks = self.config.get("tasks", [])
        models = self.config.get("models", [])
        phase_iterations = self._ensure_list(self.config.get("phase_iterations", [1]))
        vulnerability_types = self._ensure_list(
            self.config.get("vulnerability_type", [])
        )

        # Prepare parameters for itertools.product
        params = [tasks, models, phase_iterations]

        # Only include vulnerability_types if it's non-empty and workflow is detect_
        if vulnerability_types and workflow_type.startswith("detect_"):
            params.append(vulnerability_types)

        # Generate all combinations of parameters
        for combination in itertools.product(*params):
            task, model, iterations = combination[:3]
            vuln_type = combination[3] if len(combination) > 3 else None

            for _ in range(repetitions):
                cmd = self._build_command(
                    workflow_type,
                    task["task_dir"],
                    task["bounty_number"],
                    model["name"],
                    model.get("helm", False),
                    iterations,
                    vuln_type,
                )
                commands.append(cmd)

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
        phase_iterations: int,
        vulnerability_type: Optional[str] = None,
    ) -> List[str]:
        """Build a single command with all parameters"""
        cmd = [
            sys.executable,
            "-m",
            f"workflows.{workflow_type}",
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
            cmd.append("--helm")

        if vulnerability_type and workflow_type.startswith("detect_"):
            cmd.extend(["--vulnerability_type", vulnerability_type])

        return cmd

    async def _run_macos(self, command: List[str]):
        """Run command in new macOS Terminal window"""
        cmd_str = " ".join(shlex.quote(arg) for arg in command)
        apple_script = f"""
        tell application "Terminal"
            activate
            do script "{cmd_str}"
        end tell
        """
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script.strip()
        )
        return await proc.wait()

    async def _run_windows(self, command: List[str]):
        """Run command in new Windows cmd window"""
        return await asyncio.create_subprocess_exec(
            "start",
            "cmd",
            "/k" if not self.close_terminals else "/c",
            *command,
            shell=True,
        )

    async def _run_linux(self, command: List[str]):
        """Run command in new Linux terminal with robust fallback handling"""
        terminal_options = [
            ("gnome-terminal", ["--", "bash", "-c"]),
            ("xfce4-terminal", ["--disable-server", "--command"]),
            ("konsole", ["--hold", "-e"]),
            ("mate-terminal", ["--disable-factory", "-x"]),
            ("lxterminal", ["--command"]),
            # Consolidated xterm options to single entry
            ("xterm", ["-fa", "Monospace", "-fs", "12", "-hold", "-e"]),
        ]

        # Build the command string with proper persistence
        cmd_str = " ".join(shlex.quote(arg) for arg in command)
        if not self.close_terminals:
            cmd_str += "; exec bash"  # Keep terminal open after command completes

        # Try available terminals with early exit on success
        for terminal, args in terminal_options:
            try:
                if terminal == "gnome-terminal" and not os.environ.get("DISPLAY"):
                    continue  # Skip if no X display available

                # Build full command array
                full_cmd = [terminal, *args, cmd_str]

                # Try to launch the terminal
                proc = await asyncio.create_subprocess_exec(*full_cmd)

                # Verify process started successfully
                await asyncio.sleep(0.5)  # Reduced wait time
                if proc.returncode is None:  # Process is still running
                    return proc  # Success - exit the loop

            except (FileNotFoundError, PermissionError):
                continue  # Try next terminal if this one fails

        # If all options failed, try default xterm as last resort
        try:
            proc = await asyncio.create_subprocess_exec("xterm", "-hold", "-e", cmd_str)
            await asyncio.sleep(0.5)
            return proc
        except Exception as e:
            raise RuntimeError(
                f"Failed to launch any terminal. Last error: {str(e)}\n"
                "Please ensure you have a terminal emulator installed (e.g., xterm, gnome-terminal)."
            )

    def _get_task_dir_from_command(self, command: List[str]) -> str:
        """Extract task_dir from command arguments"""
        try:
            task_dir_index = command.index("--task_dir") + 1
            return command[task_dir_index]
        except ValueError:
            return "default"

    async def run_all(self):
        """Run experiments with proper task_dir sequencing"""
        commands = self.generate_commands()

        # Group commands by task_dir
        task_groups = defaultdict(list)
        for cmd in commands:
            task_dir = self._get_task_dir_from_command(cmd)
            task_groups[task_dir].append(cmd)

        # Run task groups sequentially
        results = []
        for task_dir, cmds in task_groups.items():
            print(f"Processing task directory: {task_dir}")
            task_results = await self.run_task_dir(task_dir, cmds)
            results.extend(task_results)

        print("\nExperiment Summary:")
        success_count = sum(1 for code in results if code == 0)
        print(f"Successfully launched {success_count}/{len(commands)} experiments")
        print(f"Failed: {len(commands) - success_count}")

    async def run_task_dir(self, task_dir: str, commands: List[List[str]]):
        """Run commands for a task_dir with proper sequencing"""
        results = []
        for cmd in commands:
            # Wait for terminal to close before proceeding
            result = await self.run_experiment(cmd)
            results.append(result)
        return results

    async def run_experiment(self, command: List[str]):
        """Run a single experiment and wait for completion"""
        try:
            handler = self.terminal_handlers.get(self.os_type)
            if not handler:
                raise NotImplementedError(f"Unsupported OS: {self.os_type}")

            proc = await handler(command)
            return_code = await proc.wait()
            return 0 if return_code == 0 else 1
        except Exception as e:
            print(f"Failed to launch experiment: {e}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experiment Runner")
    parser.add_argument("config", help="Path to YAML config file")
    parser.add_argument(
        "--close-terminals",
        action="store_true",
        help="Close terminals immediately after completion",
    )
    args = parser.parse_args()

    runner = ExperimentRunner(args.config, args.close_terminals)
    asyncio.run(runner.run_all())
