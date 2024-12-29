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
from utils.websocket_manager import websocket_manager

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active workflow instances
active_workflows: Dict[str, dict] = {}

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
            "status": "initialized"
        }
        
        # Initialize workflow logger
        workflow_logger.initialize(
            workflow_name=workflow_data['workflow_name'],
            task_repo_dir=workflow_data['task_repo_dir'],
            bounty_number=workflow_data['bounty_number']
        )
        
        # Return workflow ID immediately
        return {
            "workflow_id": workflow_id,
            "status": "initialized"
        }
        
    except Exception as e:
        return {
            "error": str(e)
        }

@app.post("/workflow/execute/{workflow_id}")
async def execute_workflow(workflow_id: str):
    """Execute a workflow after WebSocket connection is established"""
    if workflow_id not in active_workflows:
        return {"error": "Workflow not found"}
    
    try:
        # Start workflow execution in background
        asyncio.create_task(run_workflow(workflow_id))
        return {"status": "executing"}
    except Exception as e:
        return {"error": str(e)}

async def run_workflow(workflow_id: str):
    """Run workflow in background and broadcast updates"""
    if workflow_id not in active_workflows:
        return
    
    workflow_data = active_workflows[workflow_id]
    workflow = workflow_data["instance"]
    
    try:
        workflow_data["status"] = "running"
        await websocket_manager.broadcast(workflow_id, {
            "type": "status_update",
            "status": "running"
        })
        
        # Run the workflow
        await workflow.run()
        
        workflow_data["status"] = "completed"
        await websocket_manager.broadcast(workflow_id, {
            "type": "status_update",
            "status": "completed"
        })
        
    except Exception as e:
        workflow_data["status"] = "error"
        await websocket_manager.broadcast(workflow_id, {
            "type": "status_update",
            "status": "error",
            "error": str(e)
        })

@app.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    await websocket_manager.connect(workflow_id, websocket)
    
    try:
        # Send initial workflow state
        if workflow_id in active_workflows:
            workflow_data = active_workflows[workflow_id]
            await websocket.send_json({
                "type": "initial_state",
                "status": workflow_data["status"]
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
            elif data.get("type") == "start_execution":
                # Start workflow execution when frontend is ready
                asyncio.create_task(run_workflow(workflow_id))
    except WebSocketDisconnect:
        websocket_manager.disconnect(workflow_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        websocket_manager.disconnect(workflow_id, websocket)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
