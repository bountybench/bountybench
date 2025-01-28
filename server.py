from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Dict
from pathlib import Path
from pydantic import BaseModel
import uvicorn
import signal
import sys
from contextlib import asynccontextmanager

from workflows.detect_workflow import DetectWorkflow
from workflows.exploit_and_patch_workflow import ExploitAndPatchWorkflow
from workflows.patch_workflow import PatchWorkflow
from workflows.chat_workflow import ChatWorkflow
from utils.websocket_manager import websocket_manager

class ServerState:
    def __init__(self):
        self.active_workflows: Dict[str, dict] = {}
        self.should_exit = False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\nShutdown signal received. Cleaning up...")
        self.should_exit = True
        # Close all WebSocket connections
        for workflow_id in list(websocket_manager.active_connections.keys()):
            for connection in list(websocket_manager.active_connections[workflow_id]):
                try:
                    connection.close()
                except:
                    pass
        sys.exit(0)

state = ServerState()
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register signal handlers
signal.signal(signal.SIGINT, state.signal_handler)
signal.signal(signal.SIGTERM, state.signal_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await shutdown_event()

async def shutdown_event():
    """Handle FastAPI shutdown event"""
    state.should_exit = True
    # Close all WebSocket connections
    for workflow_id in list(websocket_manager.active_connections.keys()):
        for connection in list(websocket_manager.active_connections[workflow_id]):
            try:
                await connection.close()
            except:
                pass

app.router.lifespan = lifespan

id_to_workflow = {
    "Detect Workflow": DetectWorkflow,
    "Exploit and Patch Workflow": ExploitAndPatchWorkflow,
    "Patch Workflow": PatchWorkflow,
    "Chat Workflow": ChatWorkflow
}

@app.get("/workflow/list")
async def list_workflows():
    """List available workflow types"""
    return {
        "workflows": [
            {
                "id": "detect",
                "name": "Detect Workflow",
                "description": "Workflow for detecting and exploiting vulnerabilities"
            },
            {
                "id": "exploit_and_patch",
                "name": "Exploit and Patch Workflow",
                "description": "Workflow for exploiting and patching vulnerabilities"
            },
            {
                "id": "patch",
                "name": "Patch Workflow",
                "description": "Workflow for patching vulnerabilities"
            },
            {
                "id": "chat",
                "name": "Chat Workflow",
                "description": "Workflow for chatting"
            }
        ]
    }

@app.post("/workflow/start")
async def start_workflow(workflow_data: dict):
    """Start a new workflow instance"""
    try:
        # Initialize workflow instance
        workflow = id_to_workflow[workflow_data['workflow_name']](
            task_dir=Path(workflow_data['task_dir']),
            bounty_number=workflow_data['bounty_number'],
            interactive=workflow_data.get('interactive', False),
            phase_iterations=int(workflow_data['iterations'])
        )
        
        workflow_id = workflow.workflow_message.workflow_id
        # Store workflow instance
        state.active_workflows[workflow_id] = {
            "instance": workflow,
            "status": "initializing"
        }

        # Return workflow ID immediately
        return {
            "workflow_id": workflow_id,
            "status": "initializing"
        }
        
    except Exception as e:
        return {
            "error": str(e)
        }

@app.post("/workflow/execute/{workflow_id}")
async def execute_workflow(workflow_id: str):
    """Execute a workflow after WebSocket connection is established"""
    if workflow_id not in state.active_workflows:
        return {"error": "Workflow not found"}
    
    try:
        # Start workflow execution in background
        asyncio.create_task(run_workflow(workflow_id))
        return {"status": "executing"}
    except Exception as e:
        return {"error": str(e)}

async def run_workflow(workflow_id: str):
    if workflow_id not in state.active_workflows or state.should_exit:
        print(f"Workflow {workflow_id} not found or should exit")
        return
    
    workflow_data = state.active_workflows[workflow_id]
    workflow = workflow_data["instance"]
    
    try:
        workflow_data["status"] = "running"
        await websocket_manager.broadcast(workflow_id, {
            "message_type": "status_update",
            "status": "running"
        })
        
        # Run the workflow
        await workflow.run()

        if not state.should_exit:
            workflow_data["status"] = "completed"
            await websocket_manager.broadcast(workflow_id, {
                "message_type": "status_update",
                "status": "completed"
            })
        
    except Exception as e:
        if not state.should_exit:
            print(f"Workflow error: {e}")
            workflow_data["status"] = "error"
            await websocket_manager.broadcast(workflow_id, {
                "message_type": "status_update",
                "status": "error",
                "error": str(e)
            })
            print(f"Broadcasted error status for {workflow_id}")

@app.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    try:
        # Connect and initialize the WebSocket
        await websocket_manager.connect(workflow_id, websocket)
        print(f"WebSocket connected for workflow {workflow_id}")
        
        # Send initial connection acknowledgment
        await websocket.send_json({
            "message_type": "connection_established",
            "workflow_id": workflow_id,
            "status": "connected"
        })
        
        # Check if workflow can be executed and start it automatically
        if workflow_id in state.active_workflows:
            workflow_data = state.active_workflows[workflow_id]
            current_status = workflow_data.get("status", "unknown")
            if current_status not in ["running", "completed"]:
                print(f"Auto-starting workflow {workflow_id}")
                asyncio.create_task(run_workflow(workflow_id))
                await websocket.send_json({
                    "message_type": "workflow_status",
                    "status": "starting",
                    "can_execute": False
                })
            else:
                await websocket.send_json({
                    "message_type": "workflow_status",
                    "status": current_status,
                    "can_execute": False
                })
        else:
            # If workflow doesn't exist yet, start it
            print(f"Auto-starting new workflow {workflow_id}")
            asyncio.create_task(run_workflow(workflow_id))
            await websocket.send_json({
                "message_type": "workflow_status",
                "status": "starting",
                "can_execute": False
            })
        
        # Handle incoming messages
        while not state.should_exit:
            try:
                data = await websocket.receive_json()
                if state.should_exit:
                    break

                if data.get("type") == "pong":
                    # Update last heartbeat time in websocket manager
                    websocket_manager.update_heartbeat(workflow_id, websocket)
                    continue

                if data.get("message_type") == "user_message" and workflow_id in state.active_workflows:
                    workflow = state.active_workflows[workflow_id]["instance"]
                    if workflow.interactive:
                        result = await workflow.add_user_message(data["content"])
                        await websocket_manager.broadcast(workflow_id, {
                            "message_type": "user_message_response",
                            "content": result
                        })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error handling WebSocket message: {e}")
                if "disconnect" in str(e).lower():
                    break
                    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for workflow {workflow_id}")
    except Exception as e:
        print(f"WebSocket error for workflow {workflow_id}: {e}")
    finally:
        websocket_manager.disconnect(workflow_id, websocket)
        print(f"Cleaned up connection for workflow {workflow_id}")

class MessageInputData(BaseModel):
    message_id: str
    new_input_data: str
    
class MessageData(BaseModel):
    message_id: str

async def next_iteration(workflow_id: str):
    if workflow_id not in state.active_workflows:
        return {"error": "Workflow not found"}
    
    workflow = state.active_workflows[workflow_id]["instance"]
    if hasattr(workflow, 'next_iteration_event'):
        workflow.next_iteration_event.set()
        return {"status": "next iteration triggered"}
    else:
        return {"error": "Workflow is not in interactive mode"}

@app.post("/workflow/next/{workflow_id}")
async def next_message(workflow_id: str):
    if workflow_id not in state.active_workflows:
        return {"error": f"Workflow {workflow_id} not found"}

    workflow = state.active_workflows[workflow_id]["instance"]
    try:
        result = await workflow.run_next_message()
        if not result:
            result = await next_iteration(workflow_id)
            return result  # Return the dictionary directly
            
        print(f"Received result : {result.id}")
        return {"status": "updated", "result": result.id}
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in next_message: {str(e)}\n{error_traceback}")
        return {"error": str(e), "traceback": error_traceback}

@app.post("/workflow/rerun-message/{workflow_id}")
async def next_message(workflow_id: str, data: MessageData):
    print(f"Rerunning message: {data.message_id}")
    if workflow_id not in state.active_workflows:
        return {"error": f"Workflow {workflow_id} not found"}

    workflow = state.active_workflows[workflow_id]["instance"]

    try:
        result = await workflow.rerun_message(data.message_id)

        return {"status": "updated", "result": result.id}
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        return {"error": str(e), "traceback": error_traceback}

@app.post("/workflow/edit-message/{workflow_id}")
async def edit_action_input(workflow_id: str, data: MessageInputData):
    print(f"Editing message: {data.message_id}")
    if workflow_id not in state.active_workflows:
        return {"error": f"Workflow {workflow_id} not found"}

    workflow = state.active_workflows[workflow_id]["instance"]

    try:
        result = await workflow.edit_one_message(data.message_id, data.new_input_data)
        
        return {"status": "updated", "result": result.id}
    except Exception as e:
        return {"error": str(e)}

@app.post("/workflow/{workflow_id}/interactive")
async def update_interactive_mode(workflow_id: str, data: dict):
    print(f"Received request to update interactive mode for workflow {workflow_id}")
    print(f"Data received: {data}")
    
    try:
        if workflow_id not in state.active_workflows:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow = state.active_workflows[workflow_id]["instance"]
        new_interactive_mode = data.get("interactive")
        
        if new_interactive_mode is None:
            raise HTTPException(status_code=400, detail="Interactive mode not specified")
        
        print(f"Attempting to set interactive mode to {new_interactive_mode}")
        await workflow.set_interactive_mode(new_interactive_mode)
        print(f"Interactive mode successfully set to {new_interactive_mode}")
        
        return {"status": "success", "interactive": new_interactive_mode}
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/workflow/last-message/{workflow_id}")
async def last_message(workflow_id: str):
    if workflow_id not in state.active_workflows:
        return {"error": "Workflow not found"}
    
    workflow = state.active_workflows[workflow_id]["instance"]
    last_message_str = await workflow.get_last_message()
    return {
                "message_type": "last_message",
                "content": last_message_str
            }

@app.get("/workflow/first-message/{workflow_id}")
async def first_message(workflow_id: str):
    if workflow_id not in state.active_workflows:
        return {"error": "Workflow not found"}
    
    workflow = state.active_workflows[workflow_id]["instance"]
    first_message_str = workflow.initial_prompt
    return {
                "message_type": "first_message",
                "content": first_message_str
            }
    
@app.get("/workflow/{workflow_id}/resources")
async def get_workflow_resources(workflow_id: str):
    if workflow_id not in state.active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow = state.active_workflows[workflow_id]["instance"]
    
    # Implement a method in your workflow class to get the current resources
    resources = workflow.resource_manager.resources
    
    return resources
    
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)