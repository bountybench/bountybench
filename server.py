from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Dict, List, Optional
import json
from pathlib import Path
from datetime import datetime
import uvicorn
import signal
import sys

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

# Store active workflow instances and connections
active_workflows: Dict[str, dict] = {}
should_exit = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global should_exit
    print("\nShutdown signal received. Cleaning up...")
    should_exit = True
    # Close all WebSocket connections
    for workflow_id in list(websocket_manager.active_connections.keys()):
        for connection in list(websocket_manager.active_connections[workflow_id]):
            try:
                connection.close()
            except:
                pass
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.on_event("shutdown")
async def shutdown_event():
    """Handle FastAPI shutdown event"""
    global should_exit
    should_exit = True
    # Close all WebSocket connections
    for workflow_id in list(websocket_manager.active_connections.keys()):
        for connection in list(websocket_manager.active_connections[workflow_id]):
            try:
                await connection.close()
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
    global should_exit
    
    if workflow_id not in active_workflows or should_exit:
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
        print(f"Starting workflow.run() for {workflow_id}...")
        await workflow.run()
        print(f"Workflow.run() completed for {workflow_id}...")

        if not should_exit:
            workflow_data["status"] = "completed"
            await websocket_manager.broadcast(workflow_id, {
                "type": "status_update",
                "status": "completed"
            })
        
    except Exception as e:
        if not should_exit:
            print(f"Workflow error: {e}")
            workflow_data["status"] = "error"
            await websocket_manager.broadcast(workflow_id, {
                "type": "status_update",
                "status": "error",
                "error": str(e)
            })

@app.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    global should_exit
    
    try:
        await websocket_manager.connect(workflow_id, websocket)
        print(f"WebSocket connected for workflow {workflow_id}")
        
        # Send initial workflow state
        if workflow_id in active_workflows:
            workflow_data = active_workflows[workflow_id]
            await websocket.send_json({
                "type": "initial_state",
                "status": workflow_data["status"]
            })
            print(f"Sent initial state for workflow {workflow_id}: {workflow_data['status']}")
        
        # Handle incoming messages
        while not should_exit:
            try:
                data = await websocket.receive_json()
                if should_exit:
                    break
                    
                print(f"Received message from workflow {workflow_id}: {data}")
                
                if data.get("type") == "user_input" and workflow_id in active_workflows:
                    workflow = active_workflows[workflow_id]["instance"]
                    if workflow.interactive:
                        # TODO: Implement user input handling
                        pass
                elif data.get("type") == "start_execution":
                    print(f"Starting execution for workflow {workflow_id}")
                    asyncio.create_task(run_workflow(workflow_id))
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for workflow {workflow_id}")
                break
            except Exception as e:
                print(f"Error handling message: {e}")
                if "disconnect" in str(e).lower():
                    break
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for workflow {workflow_id}")
    except Exception as e:
        print(f"WebSocket error for workflow {workflow_id}: {e}")
    finally:
        websocket_manager.disconnect(workflow_id, websocket)
        print(f"Cleaned up connection for workflow {workflow_id}")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
