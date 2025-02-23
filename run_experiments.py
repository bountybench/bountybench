import argparse
import asyncio
import itertools
import platform
import shlex
import shutil
import sys
from collections import defaultdict
from typing import Dict, List, Optional

import yaml


class ExperimentRunner:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.os_type = platform.system()
        self.terminal_handlers = {
            "Darwin": self._run_macos,
            "Linux": self._run_linux,
            "Windows": self._run_windows,
        }

    def _load_config(self, path: str) -> Dict:
        with open(path) as f:
            return yaml.safe_load(f)

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
            "/c",
            *command,
            shell=True,
        )

    async def _run_linux(self, command: List[str]):
        """Run command in a terminal in Linux"""
        cmd_str = " ".join(shlex.quote(arg) for arg in command)

        # Handle the various terminal options
        terminals = [
            ("xterm", ["-fa", "Monospace", "-fs", "12", "-e"]),
            ("xfce4-terminal", ["--disable-server", "--command"]),
            ("mate-terminal", ["--disable-factory", "-e"]),
            ("lxterminal", ["--command"]),
            ("konsole", ["-e"]),
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
                "-e",
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

    async def run_all(self):
        """Run experiments with proper task_dir sequencing"""
        commands = self.generate_commands()

        # Group commands by task_dir
        task_groups = defaultdict(list)
        for cmd in commands:
            task_dir = self._get_task_dir_from_command(cmd)
            task_groups[task_dir].append(cmd)

        # Create tasks for each task_dir group
        tasks = []
        for task_dir, cmds in task_groups.items():
            print(f"Preparing task group for directory: {task_dir}")
            tasks.append(self.run_task_dir(task_dir, cmds))

        # Run all task groups in parallel
        all_results = await asyncio.gather(*tasks)

        # Flatten results
        results = [result for group_result in all_results for result in group_result]

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

    args = parser.parse_args()

    runner = ExperimentRunner(args.config)
    asyncio.run(runner.run_all())
