from typing import Dict, List, Any
from fastapi import WebSocket
from pathlib import Path
import asyncio

class FakeWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, workflow_id: str, websocket: WebSocket):
        if workflow_id not in self.active_connections:
            self.active_connections[workflow_id] = []
        self.active_connections[workflow_id].append(websocket)

    def disconnect(self, workflow_id: str, websocket: WebSocket):
        if workflow_id in self.active_connections:
            self.active_connections[workflow_id].remove(websocket)
            if not self.active_connections[workflow_id]:
                del self.active_connections[workflow_id]

    async def broadcast(self, workflow_id: str, message: dict):
        for connection in self.active_connections.get(workflow_id, []):
            await connection.send_json(message)


class FakeWorkflow:
    def __init__(self, task_dir: Path, bounty_number: int, interactive: bool, phase_iterations: int):
        self.workflow_message = type('obj', (object,), {'workflow_id': f'fake-{bounty_number}'})
        self.interactive = interactive
        self.phase_iterations = phase_iterations
        self.resource_manager = type('obj', (object,), {'resources': {}})()
        self.initial_prompt = "This is a fake initial prompt."

    async def run(self):
        # Simulate some asynchronous work
        await asyncio.sleep(0.1)

    async def add_user_message(self, content: str) -> str:
        return "Fake user message response."

    async def run_next_message(self) -> Any:
        return type('obj', (object,), {'id': 'fake-message-id'})()

    async def rerun_message(self, message_id: str) -> Any:
        return type('obj', (object,), {'id': 'fake-rerun-message-id'})()

    async def edit_one_message(self, message_id: str, new_input_data: str) -> Any:
        return type('obj', (object,), {'id': 'fake-edited-message-id'})()

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

class FakeChatWorkflow(FakeWorkflow):
    pass