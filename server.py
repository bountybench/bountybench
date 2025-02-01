from typing import Callable, Dict

import uvicorn
from fastapi import FastAPI

from backend.server import Server
from utils.websocket_manager import WebSocketManager, websocket_manager
from workflows.chat_workflow import ChatWorkflow
from workflows.detect_workflow import DetectWorkflow
from workflows.exploit_and_patch_workflow import ExploitAndPatchWorkflow
from workflows.patch_workflow import PatchWorkflow


def create_app(
    ws_manager: WebSocketManager = None, workflow_factory: Dict[str, Callable] = None
):
    if ws_manager is None:
        ws_manager = websocket_manager

    if workflow_factory is None:
        workflow_factory = {
            "Detect Workflow": DetectWorkflow,
            "Exploit and Patch Workflow": ExploitAndPatchWorkflow,
            "Patch Workflow": PatchWorkflow,
            "Chat Workflow": ChatWorkflow,
        }

    app = FastAPI()
    server = Server(app, ws_manager, workflow_factory)
    return server.app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
