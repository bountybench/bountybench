from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import signal
import sys
from typing import Dict, Set, Type
from pathlib import Path
import importlib
import inspect
import pkgutil

from workflows.base_workflow import BaseWorkflow
from utils.logger import get_main_logger
from .models import WorkflowStartRequest

logger = get_main_logger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()

# Store active workflows
active_workflows: Dict[str, BaseWorkflow] = {}

# Store tasks for cleanup
background_tasks: Set[asyncio.Task] = set()

def handle_shutdown(signum, frame):
    """Handle shutdown gracefully"""
    logger.info("Shutting down server...")
    
    # Cancel all background tasks
    for task in background_tasks:
        task.cancel()
    
    # Close all WebSocket connections
    for connection in active_connections:
        asyncio.create_task(connection.close())
    
    # Stop all workflows
    for workflow in active_workflows.values():
        if hasattr(workflow, 'cleanup'):
            asyncio.create_task(workflow.cleanup())
    
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

class WorkflowManager:
    """Manages workflow discovery, instantiation and monitoring"""
    
    @staticmethod
    def discover_workflows() -> Dict[str, Type[BaseWorkflow]]:
        """Automatically discover all workflow classes in the workflows directory"""
        workflows = {}
        workflows_dir = Path(__file__).parent.parent / "workflows"
        
        for _, name, _ in pkgutil.iter_modules([str(workflows_dir)]):
            module = importlib.import_module(f"workflows.{name}")
            for item_name, item in inspect.getmembers(module):
                if (inspect.isclass(item) and 
                    issubclass(item, BaseWorkflow) and 
                    item != BaseWorkflow):
                    workflows[item_name] = item
        
        return workflows

    @staticmethod
    async def monitor_workflow(workflow_id: str, workflow: BaseWorkflow):
        """Monitor workflow execution and send updates via WebSocket"""
        try:
            for phase_response, phase_success in workflow.run_phases():
                # Prepare update message
                update = {
                    "type": "phase_update",
                    "workflow_id": workflow_id,
                    "data": {
                        "phase_idx": workflow._current_phase_idx,
                        "phase_name": workflow.current_phase.phase_name if workflow.current_phase else None,
                        "status": workflow.status.value if hasattr(workflow.status, 'value') else str(workflow.status),
                        "response": phase_response.to_dict() if hasattr(phase_response, 'to_dict') else str(phase_response),
                        "success": phase_success,
                        "iteration_count": getattr(workflow, '_workflow_iteration_count', 0)
                    }
                }
                
                # Broadcast update to all connected clients
                await broadcast_message(update)
                
                if not phase_success:
                    break
                    
        except Exception as e:
            error_message = {
                "type": "error",
                "workflow_id": workflow_id,
                "data": {
                    "error_type": type(e).__name__,
                    "message": str(e)
                }
            }
            await broadcast_message(error_message)
            logger.error(f"Error in workflow {workflow_id}: {e}")
            raise

async def broadcast_message(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")

@app.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle user input for interactive mode
            if data["type"] == "user_input" and workflow_id in active_workflows:
                workflow = active_workflows[workflow_id]
                if hasattr(workflow, "handle_user_input"):
                    await workflow.handle_user_input(data["input"])
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.post("/workflow/start")
async def start_workflow(request: WorkflowStartRequest):
    """Start a new workflow instance"""
    workflows = WorkflowManager.discover_workflows()
    if request.workflow_name not in workflows:
        return {"error": f"Workflow {request.workflow_name} not found"}
    
    workflow_class = workflows[request.workflow_name]
    workflow = workflow_class(
        task_repo_dir=Path(request.task_repo_dir),
        bounty_number=request.bounty_number,
        interactive=request.interactive
    )
    
    workflow_id = f"{request.workflow_name}_{request.bounty_number}"
    active_workflows[workflow_id] = workflow
    
    # Start monitoring the workflow in the background
    task = asyncio.create_task(WorkflowManager.monitor_workflow(workflow_id, workflow))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    
    return {"workflow_id": workflow_id}

@app.get("/workflow/list")
async def list_workflows():
    """List all available workflows"""
    workflows = WorkflowManager.discover_workflows()
    return {
        "workflows": [
            {
                "name": name,
                "description": workflow.__doc__ or "No description available"
            }
            for name, workflow in workflows.items()
        ]
    }

@app.get("/workflow/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get current status of a workflow"""
    if workflow_id not in active_workflows:
        return {"error": "Workflow not found"}
    
    workflow = active_workflows[workflow_id]
    return {
        "status": workflow.status,
        "current_phase": workflow.current_phase.phase_name if workflow.current_phase else None,
        "phase_idx": workflow._current_phase_idx,
        "iteration_count": workflow._workflow_iteration_count
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
