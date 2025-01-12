from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Dict, Optional, Set, Any
from pathlib import Path
import uuid
import logging
from datetime import datetime, timedelta
from pydantic import BaseModel

# Import workflow classes
from workflows.exploit_and_patch_workflow import ExploitAndPatchWorkflow
from workflows.patch_workflow import PatchWorkflow

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
active_websockets: Set[WebSocket] = set()

# Store running workflows
running_workflows: Dict[str, Any] = {}

# Store workflow pause states
workflow_pauses: Dict[str, asyncio.Event] = {}

# Store pending messages for interactive mode
pending_messages: Dict[str, Dict] = {}
pending_workflows: Dict[str, Dict] = {}

class WorkflowStartRequest(BaseModel):
    workflow_type: str
    task_dir: str
    bounty_number: str
    interactive: bool = False

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    active_websockets.add(websocket)
    logger.info("WebSocket connection established")
    
    try:
        while True:
            message = await websocket.receive_json()
            await handle_websocket_message(websocket, message)
    except:
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
    finally:
        active_websockets.remove(websocket)
        logger.info("WebSocket connection closed")

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
        logger.info(f"Starting workflow {workflow_id} (interactive: {interactive})")
        
        # Create custom logger for this workflow
        ws_logger = WebSocketLogger(workflow_id)
        
        # Attach logger methods to workflow instance
        workflow_instance.broadcast_message = ws_logger.log_message
        if interactive:
            workflow_instance.request_user_input = ws_logger.request_user_input
        
        logger.info("Running workflow...")
        # Run the workflow
        await workflow_instance.run_async()
        logger.info(f"Workflow {workflow_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in workflow {workflow_id}: {str(e)}", exc_info=True)
        await broadcast_message({
            "type": "error",
            "workflow_id": workflow_id,
            "error": str(e)
        })
        # Remove the workflow from running workflows
        if workflow_id in running_workflows:
            del running_workflows[workflow_id]
        raise

async def wait_for_websocket(workflow_id: str, timeout: float = 10.0) -> bool:
    """Wait for WebSocket connection to be established"""
    start_time = datetime.now()
    while datetime.now() - start_time < timedelta(seconds=timeout):
        if active_websockets:
            return True
        await asyncio.sleep(0.1)
    return False

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
    try:
        logger.info(f"Starting workflow with type: {request.workflow_type}")
        
        if request.workflow_type not in ["exploit_and_patch", "patch"]:
            raise HTTPException(status_code=400, detail="Invalid workflow type")
        
        # Create a unique ID for this workflow
        workflow_id = str(uuid.uuid4())
        
        # Wait for WebSocket connection
        if not await wait_for_websocket(workflow_id):
            raise HTTPException(
                status_code=503,
                detail="WebSocket connection not established. Please ensure the client is connected."
            )
        
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
        
        logger.info(f"Workflow {workflow_id} started successfully")
        return {"workflow_id": workflow_id, "status": "started"}
        
    except Exception as e:
        logger.error(f"Error starting workflow: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflow/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get the status of a running workflow"""
    if workflow_id not in running_workflows:
        return {"status": "completed"}
    return {"status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
