from typing import Callable, Dict

import uvicorn
from fastapi import FastAPI

from backend.server import Server
from utils.websocket_manager import WebSocketManager, websocket_manager
from workflows.chat_workflow import ChatWorkflow
from workflows.detect_patch_workflow import DetectPatchWorkflow
from workflows.exploit_patch_workflow import ExploitPatchWorkflow
from workflows.patch_workflow import PatchWorkflow


def create_app(
    ws_manager: WebSocketManager = None, workflow_factory: Dict[str, Callable] = None
):
    if ws_manager is None:
        ws_manager = websocket_manager

    if workflow_factory is None:
        workflow_factory = {
            "Detect Patch Workflow": DetectPatchWorkflow,
            "Exploit and Patch Workflow": ExploitPatchWorkflow,
            "Patch Workflow": PatchWorkflow,
            "Chat Workflow": ChatWorkflow,
        }

    app = FastAPI()
    server = Server(app, ws_manager, workflow_factory)
    return server.app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=7999, reload=False)
