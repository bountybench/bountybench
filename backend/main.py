from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Dict, Optional, Set, Any
from pathlib import Path
import uuid
from datetime import datetime
from pydantic import BaseModel

from workflows.exploit_and_patch_workflow import ExploitAndPatchWorkflow
from workflows.patch_workflow import PatchWorkflow

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active websocket connections
active_connections: Set[WebSocket] = set()

# Store running workflows
running_workflows: Dict[str, Any] = {}

# Store workflow pause states
workflow_pauses: Dict[str, asyncio.Event] = {}

# Store pending messages for interactive mode
pending_messages: Dict[str, Dict] = {}

class WorkflowStartRequest(BaseModel):
    workflow_type: str
    task_dir: str
    bounty_number: str
    interactive: bool = False

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            message = await websocket.receive_json()
            await handle_websocket_message(websocket, message)
    except:
        active_connections.remove(websocket)

async def handle_websocket_message(websocket: WebSocket, message: Dict):
    """Handle incoming websocket messages"""
    message_type = message.get("type")
    workflow_id = message.get("workflow_id")
    
    if message_type == "agent_response":
        # Handle user response to agent message in interactive mode
        if workflow_id in pending_messages:
            pending_messages[workflow_id]["response"] = message.get("response")
            if workflow_id in workflow_pauses:
                workflow_pauses[workflow_id].set()  # Resume workflow execution

async def broadcast_message(message: dict):
    """Broadcast message to all connected clients"""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            active_connections.remove(connection)

class WebSocketLogger:
    """Custom logger that broadcasts messages via WebSocket"""
    
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
    
    async def log_message(self, message_type: str, data: Dict):
        await broadcast_message({
            "type": message_type,
            "workflow_id": self.workflow_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
    
    async def request_user_input(self, agent_name: str, message: Dict) -> Dict:
        """Request and wait for user input in interactive mode"""
        msg_id = str(uuid.uuid4())
        pending_messages[self.workflow_id] = {"message_id": msg_id}
        
        # Create an event for this pause
        pause_event = asyncio.Event()
        workflow_pauses[self.workflow_id] = pause_event
        
        # Send message to frontend
        await broadcast_message({
            "type": "request_input",
            "workflow_id": self.workflow_id,
            "message_id": msg_id,
            "agent_name": agent_name,
            "message": message
        })
        
        # Wait for user response
        await pause_event.wait()
        
        # Get and clear the response
        response = pending_messages[self.workflow_id].get("response")
        del pending_messages[self.workflow_id]
        del workflow_pauses[self.workflow_id]
        
        return response

async def run_workflow(workflow_id: str, workflow_instance: Any, interactive: bool):
    """Run workflow in background task"""
    try:
        # Create custom logger for this workflow
        ws_logger = WebSocketLogger(workflow_id)
        
        # Attach logger methods to workflow instance
        workflow_instance.broadcast_message = ws_logger.log_message
        if interactive:
            workflow_instance.request_user_input = ws_logger.request_user_input
        
        # Run the workflow
        await workflow_instance.run_async()
        
    except Exception as e:
        await broadcast_message({
            "type": "error",
            "workflow_id": workflow_id,
            "error": str(e)
        })
    finally:
        if workflow_id in running_workflows:
            del running_workflows[workflow_id]

@app.get("/api/workflow/list")
async def list_workflows():
    """List available workflow types"""
    return {
        "workflows": [
            {
                "id": "exploit_and_patch",
                "name": "Exploit and Patch Workflow",
                "description": "Workflow for exploiting and patching vulnerabilities"
            },
            {
                "id": "patch",
                "name": "Patch Workflow",
                "description": "Workflow for patching known vulnerabilities"
            }
        ]
    }

@app.post("/api/workflow/start")
async def start_workflow(
    request: WorkflowStartRequest,
    background_tasks: BackgroundTasks
):
    """Start a new workflow"""
    if request.workflow_type not in ["exploit_and_patch", "patch"]:
        return {"error": "Invalid workflow type"}
    
    # Create a unique ID for this workflow
    workflow_id = str(uuid.uuid4())
    
    # Create workflow instance
    workflow_class = ExploitAndPatchWorkflow if request.workflow_type == "exploit_and_patch" else PatchWorkflow
    workflow_instance = workflow_class(
        task_dir=Path(request.task_dir),
        bounty_number=request.bounty_number,
        interactive=request.interactive
    )
    
    running_workflows[workflow_id] = workflow_instance
    
    # Start workflow in background task
    background_tasks.add_task(run_workflow, workflow_id, workflow_instance, request.interactive)
    
    return {"workflow_id": workflow_id, "status": "started"}

@app.get("/api/workflow/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get the status of a running workflow"""
    if workflow_id not in running_workflows:
        return {"status": "completed"}
    return {"status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
