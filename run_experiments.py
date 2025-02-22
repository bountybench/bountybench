import argparse
import asyncio
import itertools
import os
import platform
import shlex
import shutil
import sys
from pathlib import Path
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
            ("xterm", ["-fa", "Monospace", "-fs", "12", "-hold", "-e"]),
        ]

        # Build the command string with proper persistence
        cmd_str = " ".join(shlex.quote(arg) for arg in command)
        if not self.close_terminals:
            cmd_str += "; exec bash"  # Keep terminal open after command completes

        # Try available terminals
        last_error = None
        for terminal, args in terminal_options:
            try:
                # Special handling for GNOME Terminal to avoid D-Bus issues
                if terminal == "gnome-terminal":
                    # Check if we're in a proper desktop environment
                    if not os.environ.get("DISPLAY"):
                        continue  # Skip GNOME Terminal if no display available

                    # Try launching with dbus-launch if available
                    if shutil.which("dbus-launch"):
                        full_cmd = ["dbus-launch", terminal, *args, cmd_str]
                    else:
                        full_cmd = [terminal, *args, cmd_str]
                else:
                    full_cmd = [terminal, *args, cmd_str]

                # Launch the terminal
                proc = await asyncio.create_subprocess_exec(*full_cmd)
                await asyncio.sleep(1)  # Give the terminal time to launch
                if proc.returncode is None:  # Process is still running
                    return proc
                else:
                    continue  # Try next terminal
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(
            "Failed to launch terminal. Last error: {}\n"
            "Please ensure you have a terminal emulator installed (e.g., xterm, gnome-terminal).".format(
                last_error
            )
        )

    async def run_experiment(self, command: List[str]):
        """Run a single experiment with proper terminal handling"""
        try:
            handler = self.terminal_handlers.get(self.os_type)
            if not handler:
                raise NotImplementedError(f"Unsupported OS: {self.os_type}")

            proc = await handler(command)
            return 0
        except Exception as e:
            print(f"Failed to launch experiment: {e}", file=sys.stderr)
            return 1

    async def run_all(self):
        """Run all experiments with proper terminal spawning"""
        commands = self.generate_commands()
        tasks = [self.run_experiment(cmd) for cmd in commands]
        results = await asyncio.gather(*tasks)

        print("\nExperiment Summary:")
        success_count = sum(1 for code in results if code == 0)
        print(f"Successfully launched {success_count}/{len(commands)} experiments")
        print(f"Failed: {len(commands) - success_count}")


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
