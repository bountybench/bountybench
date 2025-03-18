import asyncio
from pathlib import Path
from typing import Any, Dict, List

from fastapi import WebSocket


class FakeWorkflow:
    def __init__(
        self,
        task_dir: Path,
        bounty_number: int,
        interactive: bool,
        phase_iterations: int,
    ):
        self.workflow_message = type(
            "obj", (object,), {"workflow_id": f"fake-{bounty_number}"}
        )
        self.interactive = interactive
        self.phase_iterations = phase_iterations
        self.resource_manager = type("obj", (object,), {"resources": {}})()
        self.initial_prompt = "This is a fake initial prompt."

    async def run(self):
        # Simulate some asynchronous work
        await asyncio.sleep(0.1)

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


# Define specific fake workflows if behavior varies
class FakeDetectWorkflow(FakeWorkflow):
    pass


class FakeExploitAndPatchWorkflow(FakeWorkflow):
    pass


class FakePatchWorkflow(FakeWorkflow):
    pass
