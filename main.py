from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from pathlib import Path
import uuid
import json
from typing import List, Dict, Optional

# Import workflow related modules
from workflows.exploit_and_patch_workflow_v2 import ExploitAndPatchWorkflow
from utils.workflow_logger import workflow_logger

app = FastAPI()

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active workflows
active_workflows: Dict[str, ExploitAndPatchWorkflow] = {}

class WorkflowStartRequest(BaseModel):
    workflow_name: str
    task_repo_dir: str
    bounty_number: str
    interactive: bool = True

class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    message: str

class AgentMessage(BaseModel):
    workflow_id: str
    content: str
    agent: str

@app.get("/workflow/list")
async def list_workflows():
    """List all available workflows"""
    # For now we only have one workflow type
    workflows = [{
        "name": "exploit_and_patch_workflow",
        "description": "Workflow for exploiting and patching vulnerabilities"
    }]
    return {"workflows": workflows}

@app.post("/workflow/start", response_model=WorkflowResponse)
async def start_workflow(request: WorkflowStartRequest):
    """Start a new workflow instance"""
    try:
        # Generate unique workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Create workflow instance
        if request.workflow_name == "exploit_and_patch_workflow":
            workflow = ExploitAndPatchWorkflow(
                task_repo_dir=Path(request.task_repo_dir),
                bounty_number=request.bounty_number,
                interactive=request.interactive
            )
            
            # Store workflow instance
            active_workflows[workflow_id] = workflow
            
            return WorkflowResponse(
                workflow_id=workflow_id,
                status="started",
                message="Workflow started successfully"
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown workflow type: {request.workflow_name}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get the current status of a workflow"""
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[workflow_id]
    # Get current phase and iteration from workflow logger
    return {
        "status": "running",  # This will be enhanced later
        "current_phase": workflow_logger.current_phase.phase_name if workflow_logger.current_phase else None,
        "current_iteration": workflow_logger.current_iteration.iteration_idx if workflow_logger.current_iteration else None
    }

@app.websocket("/ws/workflow/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    try:
        await websocket.accept()
        
        if workflow_id not in active_workflows:
            await websocket.send_json({
                "type": "error",
                "content": "Workflow not found"
            })
            return
            
        workflow = active_workflows[workflow_id]
        
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Process message based on type
                if message["type"] == "user_input":
                    # Handle user input for interactive mode
                    response = await process_user_input(workflow, message["content"])
                    await websocket.send_json({
                        "type": "agent_response",
                        "content": response,
                        "agent": "current_agent"  # This will be updated with actual agent
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "content": str(e)
                })
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {str(e)}")

@app.get("/workflow/{workflow_id}/logs")
async def get_workflow_logs(workflow_id: str):
    """Get all logs for a workflow"""
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Get logs from workflow logger
    try:
        log_file = workflow_logger.log_file
        if log_file and log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
            return logs
        return {"error": "No logs found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")

async def process_user_input(workflow: ExploitAndPatchWorkflow, user_input: str):
    """Process user input in interactive mode"""
    # This will be implemented based on your workflow's interactive mode
    return "Agent response to user input"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
