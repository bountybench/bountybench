import argparse
import asyncio
import itertools
from typing import Dict, List, Optional

import aiohttp
import yaml
from rich.console import Console
import websockets


class UIExperimentRunner:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
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
        vulnerability_types = self._ensure_list(self.config.get("vulnerability_type", []))
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
        self.console.print(f"Starting {len(workflows)} workflows...")

        # Register all workflows first to get their IDs
        workflow_ids = await asyncio.gather(
            *(self._register_workflow_async(wd) for wd in workflows)
        )

        # Remove failed (None) workflow IDs
        workflow_ids = [wid for wid in workflow_ids if wid is not None]

        # Run workflows concurrently in the same terminal
        await asyncio.gather(*(self._run_workflow_in_same_terminal(wid) for wid in workflow_ids))

        self.console.print("\n✅ All workflows completed.")

    async def _register_workflow_async(self, workflow_data: Dict) -> Optional[str]:
        """Register workflow asynchronously with FastAPI backend and retrieve its ID."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.backend_url}/workflow/start", json=workflow_data
                ) as response:
                    response_text = await response.text()
                    print(f"📝 Server response ({response.status}): {response_text}", flush=True)

                    if response.status == 200:
                        data = await response.json()
                        return data.get("workflow_id")
                    else:
                        print(f"❌ Failed to register workflow: {response_text}", flush=True)
                        return None
        except Exception as e:
            print(f"❌ Error registering workflow: {e}", flush=True)
            return None

    async def _run_workflow_in_same_terminal(self, workflow_id: str):
        """Run workflow and stream logs in the same terminal."""
        ws_url = f"ws://localhost:8000/ws/{workflow_id}"
        try:
            async with websockets.connect(ws_url) as ws:
                while True:
                    try:
                        await ws.recv() 
                    except websockets.exceptions.ConnectionClosed:
                        break
                    except Exception:
                        break
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experiment Runner")
    parser.add_argument("config", help="Path to YAML config file")
    args = parser.parse_args()

    runner = UIExperimentRunner(args.config)
    asyncio.run(runner.run_all())
