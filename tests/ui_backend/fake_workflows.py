import asyncio
from pathlib import Path
from typing import Any, Dict, List

from fastapi import WebSocket

from workflows.interactive_controller import InteractiveController


class FakeWorkflow:
    def __init__(
        self,
        task_dir: Path,
        bounty_number: int,
        vulnerability_type: str,
        interactive: bool,
        phase_iterations: int,
        model: str,
        use_helm: bool,
        use_mock_model,
        max_input_tokens: int = 4096,
        max_output_tokens: int = 2048,
    ):
        self.use_mock_model = use_mock_model
        self.workflow_message = type(
            "obj", (object,), {"workflow_id": f"fake-{bounty_number}"}
        )
        self.interactive = interactive
        self.phase_iterations = phase_iterations
        self.resource_manager = type("obj", (object,), {"resources": {}})()
        self.agent_manager = type("obj", (object,), {"agents": {}})()
        self.interactive_controller = FakeInteractiveController(self)
        self.status = "running"  # Simulating a workflow status
        self.next_iteration_queue = asyncio.Queue()
        self.initial_prompt = "This is a fake initial prompt."
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens

    @property
    def task(self) -> Dict[str, Any]:
        """Return a fake task representation."""
        return {"description": "Fake task for testing", "id": "fake-task-id"}

    @property
    def current_phase(self):
        """Return a fake phase representation."""
        return None

    async def run(self):
        """Simulate running workflow asynchronously."""
        await asyncio.sleep(0.1)

    async def stop(self):
        """Simulate stopping a workflow properly."""
        self.status = "stopped"

        # Simulate deallocating agents and resources
        self.agent_manager.agents.clear()
        self.resource_manager.resources.clear()

        # Ensure no lingering async events (preventing unexpected executions)
        # self.next_iteration_queue.clear()

        # Simulate finalizing workflow
        await self._finalize_workflow()

    async def _finalize_workflow(self):
        """Simulate finalizing workflow - saves workflow state."""
        self.status = "INCOMPLETE"


# Define specific fake workflows if behavior varies
class FakeDetectPatchWorkflow(FakeWorkflow):
    pass


class FakeExploitPatchWorkflow(FakeWorkflow):
    pass


class FakePatchWorkflow(FakeWorkflow):
    pass


class FakeChatWorkflow(FakeWorkflow):
    pass


class FakeInteractiveController(InteractiveController):
    async def run_next_message(self) -> Any:
        return type("obj", (object,), {"id": "fake-message-id"})()

    async def run_message(self, message_id: str) -> Any:
        return type("obj", (object,), {"id": "fake-run-message-id"})()

    async def edit_one_message(self, message_id: str, new_input_data: str) -> Any:
        return type("obj", (object,), {"id": "fake-edited-message-id"})()

    async def set_interactive_mode(self, mode: bool):
        self.interactive = mode

    async def get_last_message(self) -> str:
        return "This is the last fake message."
