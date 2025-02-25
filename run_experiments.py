import argparse
import asyncio
import itertools
import os
import platform
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional

import aiohttp
import requests
import websockets
import yaml
from rich.console import Console


class ExperimentRunner:
    def __init__(self, config_path: str, hold_terminals: bool = False):
        self.config = self._load_config(config_path)
        self.os_type = platform.system()
        self.hold_terminals = hold_terminals
        self.backend_url = "http://localhost:8000"
        self.console = Console()

    def _load_config(self, path: str) -> Dict:
        with open(path) as f:
            return yaml.safe_load(f)

    def _ensure_list(self, value):
        """Ensure the input is a list (convert single values to a single-item list)"""
        return value if isinstance(value, list) else [value]

    def generate_workflow_data(self) -> List[Dict]:
        """Generate metadata for each workflow instance."""
        workflows = []
        workflow_type = self.config["workflow_type"].replace("_", " ").title()
        trials_per_config = self.config.get("trials_per_config", 1)
        tasks = self.config.get("tasks", [])
        models = self.config.get("models", [])
        phase_iterations = self._ensure_list(self.config.get("phase_iterations", [1]))
        vulnerability_types = self._ensure_list(
            self.config.get("vulnerability_type", [])
        )
        mock_model = self.config.get("use_mock_model", False)

        params = [tasks, models, phase_iterations]
        if vulnerability_types and workflow_type.startswith("detect_"):
            params.append(vulnerability_types)

        for combination in itertools.product(*params):
            task, model, iterations = combination[:3]
            vuln_type = combination[3] if len(combination) > 3 else ""

            for _ in range(trials_per_config):
                workflows.append(
                    {
                        "workflow_name": workflow_type,
                        "task_dir": task["task_dir"],
                        "bounty_number": task["bounty_number"],
                        "vulnerability_type": vuln_type,
                        "interactive": self.config.get("interactive", False),
                        "iterations": iterations,
                        "model": model["name"],
                        "use_helm": model["helm"],
                        "use_mock_model": mock_model,
                    }
                )

        return workflows

    async def run_all(self):
        workflows = self.generate_workflow_data()

        self.console.print(
            f"Starting {len(workflows)} workflows in separate terminals..."
        )

        # Register all workflows first to get their IDs
        workflow_ids = await asyncio.gather(
            *(self._register_workflow_async(wd) for wd in workflows)
        )

        # Remove any failed (None) workflow IDs
        workflow_ids = [wid for wid in workflow_ids if wid is not None]

        # Launch a separate terminal for each workflow
        await asyncio.gather(
            *(
                self._launch_terminal_for_workflow(wid, i)
                for i, wid in enumerate(workflow_ids)
            )
        )

        self.console.print(
            f"\n✅ Successfully launched {len(workflow_ids)} workflows in separate terminals."
        )

    async def _register_workflow_async(self, workflow_data: Dict) -> Optional[str]:
        """Register workflow asynchronously with FastAPI backend and retrieve its ID."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.backend_url}/workflow/start", json=workflow_data
                ) as response:
                    response_text = await response.text()
                    print(
                        f"📝 Server response ({response.status}): {response_text}",
                        flush=True,
                    )

                    if response.status == 200:
                        data = await response.json()
                        return data.get("workflow_id")
                    else:
                        print(
                            f"❌ Failed to register workflow: {response_text}",
                            flush=True,
                        )
                        return None
        except Exception as e:
            print(f"❌ Error registering workflow: {e}", flush=True)
            return None

    async def _launch_terminal_for_workflow(self, workflow_id: str, index: int):
        """Launch a new terminal window to execute the workflow via WebSocket."""
        # Create a temporary script that will connect to the WebSocket
        script_content = self._create_workflow_script(workflow_id, index)

        # Create temporary script file
        fd, script_path = tempfile.mkstemp(suffix=".py", prefix=f"workflow_{index}_")
        with os.fdopen(fd, "w") as f:
            f.write(script_content)

        # Make script executable
        os.chmod(script_path, 0o755)

        # Get the same Python interpreter that's running this script
        python_exec = sys.executable

        # Launch terminal based on OS
        if self.os_type == "Windows":
            # For Windows, use start cmd
            cmd = f'start cmd /k "{python_exec} {script_path}"'
            subprocess.Popen(cmd, shell=True)
        elif self.os_type == "Darwin":  # macOS
            # For macOS, use osascript to open Terminal
            cmd = [
                "osascript",
                "-e",
                f'tell app "Terminal" to do script "{python_exec} {script_path}"',
            ]
            subprocess.Popen(cmd)
        else:  # Linux
            # For Linux, try to detect available terminal emulators
            terminals = ["gnome-terminal", "xterm", "konsole", "terminator"]

            for term in terminals:
                try:
                    if term == "gnome-terminal":
                        subprocess.Popen([term, "--", python_exec, script_path])
                    else:
                        subprocess.Popen([term, "-e", f"{python_exec} {script_path}"])
                    break
                except FileNotFoundError:
                    continue
            else:
                self.console.print(
                    f"⚠️ Could not find a terminal emulator. Using current terminal for workflow {workflow_id}"
                )
                # Fallback to running in current process as a background task
                asyncio.create_task(self._trigger_workflow_execution(workflow_id))

        self.console.print(f"🚀 Launched terminal for workflow {workflow_id}")

    def _create_workflow_script(self, workflow_id: str, index: int) -> str:
        """Create a Python script that will connect to the WebSocket and handle a specific workflow."""
        return f"""#!/usr/bin/env python
import asyncio
import websockets
import sys

async def run_workflow():
    ws_url = "ws://localhost:8000/ws/{workflow_id}"
    try:
        print(f"Connecting to workflow {workflow_id} (#{index})...")
        async with websockets.connect(ws_url) as ws:
            print(f"🚀 Workflow {workflow_id} is running...")
            
            # Keep receiving messages until connection closes
            while True:
                try:
                    message = await ws.recv()
                    print(f"Received: {{message}}")
                except websockets.exceptions.ConnectionClosed:
                    print(f"Connection closed for workflow {workflow_id}")
                    break
                except Exception as e:
                    print(f"Error: {{e}}")
                    break
    except Exception as e:
        print(f"❌ Error connecting to WebSocket for {workflow_id}: {{e}}")
    
    if {self.hold_terminals}:
        input("Press Enter to close this terminal...")

asyncio.run(run_workflow())
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experiment Runner")
    parser.add_argument("config", help="Path to YAML config file")
    parser.add_argument(
        "--hold-terminals",
        action="store_true",
        help="Keep terminals open after completion",
    )
    args = parser.parse_args()
    runner = ExperimentRunner(args.config, args.hold_terminals)
    asyncio.run(runner.run_all())
