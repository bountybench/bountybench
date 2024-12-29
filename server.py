from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Dict, List, Optional
import json
from pathlib import Path
from datetime import datetime
import uvicorn

from workflows.exploit_and_patch_workflow_v2 import ExploitAndPatchWorkflow
from utils.workflow_logger import workflow_logger

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active workflow instances and their WebSocket connections
active_workflows: Dict[str, dict] = {}
active_connections: Dict[str, List[WebSocket]] = {}

class WorkflowManager:
    @staticmethod
    async def broadcast_update(workflow_id: str, data: dict):
        if workflow_id in active_connections:
            for connection in active_connections[workflow_id]:
                try:
                    await connection.send_json(data)
                except:
                    pass

@app.get("/workflow/list")
async def list_workflows():
    """List available workflow types"""
    return {
        "workflows": [
            {
                "id": "exploit_and_patch",
                "name": "Exploit and Patch Workflow",
                "description": "Workflow for exploiting and patching vulnerabilities"
            }
        ]
    }

@app.post("/workflow/start")
async def start_workflow(workflow_data: dict):
    """Start a new workflow instance"""
    try:
        workflow_id = f"{workflow_data['workflow_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize workflow instance
        workflow = ExploitAndPatchWorkflow(
            task_repo_dir=Path(workflow_data['task_repo_dir']),
            bounty_number=workflow_data['bounty_number'],
            interactive=workflow_data.get('interactive', False)
        )
        
        # Store workflow instance
        active_workflows[workflow_id] = {
            "instance": workflow,
            "status": "initializing",
            "current_phase": None,
            "current_iteration": None
        }
        
        # Start workflow in background
        asyncio.create_task(run_workflow(workflow_id))
        
        return {"workflow_id": workflow_id, "status": "started"}
    except Exception as e:
        return {"error": str(e)}, 400

async def run_workflow(workflow_id: str):
    """Run workflow in background and broadcast updates"""
    workflow_data = active_workflows[workflow_id]
    workflow = workflow_data["instance"]
    
    try:
        workflow_data["status"] = "running"
        await WorkflowManager.broadcast_update(workflow_id, {
            "type": "status_update",
            "status": "running"
        })
        
        # Run workflow
        workflow.run()
        
        workflow_data["status"] = "completed"
        await WorkflowManager.broadcast_update(workflow_id, {
            "type": "status_update",
            "status": "completed"
        })
    except Exception as e:
        workflow_data["status"] = "error"
        await WorkflowManager.broadcast_update(workflow_id, {
            "type": "status_update",
            "status": "error",
            "error": str(e)
        })

@app.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    await websocket.accept()
    
    if workflow_id not in active_connections:
        active_connections[workflow_id] = []
    active_connections[workflow_id].append(websocket)
    
    try:
        # Send initial workflow state
        if workflow_id in active_workflows:
            workflow_data = active_workflows[workflow_id]
            await websocket.send_json({
                "type": "initial_state",
                "status": workflow_data["status"],
                "current_phase": workflow_data["current_phase"],
                "current_iteration": workflow_data["current_iteration"]
            })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "user_input" and workflow_id in active_workflows:
                workflow = active_workflows[workflow_id]["instance"]
                # Handle user input if workflow is interactive
                if workflow.interactive:
                    # TODO: Implement user input handling
                    pass
    except WebSocketDisconnect:
        active_connections[workflow_id].remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections.get(workflow_id, []):
            active_connections[workflow_id].remove(websocket)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
