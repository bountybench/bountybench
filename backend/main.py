import os
from typing import Callable, Dict

import uvicorn
from fastapi import FastAPI

from backend.execution_backends import LocalExecutionBackend
from backend.server import Server
from utils.websocket_manager import WebSocketManager, websocket_manager
from workflows.detect_patch_workflow import DetectPatchWorkflow
from workflows.exploit_patch_workflow import ExploitPatchWorkflow
from workflows.patch_workflow import PatchWorkflow
from workflows.exploit_workflow import ExploitWorkflow


def create_app(
    ws_manager: WebSocketManager = None,
    workflow_factory: Dict[str, Callable] = None,
    backend_type: str = None,
):
    if ws_manager is None:
        ws_manager = websocket_manager

    if workflow_factory is None:
        workflow_factory = {
            "Detect Patch Workflow": DetectPatchWorkflow,
            "Exploit Patch Workflow": ExploitPatchWorkflow,
            "Patch Workflow": PatchWorkflow,
            "Exploit Workflow": ExploitWorkflow
        }

    # Determine the execution backend type
    if backend_type is None:
        backend_type = os.environ.get("EXECUTION_BACKEND", "local")

    app = FastAPI()

    # Create the appropriate execution backend
    if backend_type.lower() == "kubernetes":
        raise NotImplementedError("Kubernetes execution backend is not yet supported.")
    else:
        # Default to local execution
        execution_backend = LocalExecutionBackend(workflow_factory, app=app)

    server = Server(app, ws_manager, execution_backend)
    return server.app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=7999, reload=False)
