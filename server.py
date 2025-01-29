from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Callable, Dict
from pathlib import Path
from pydantic import BaseModel
import uvicorn
import signal
import sys
from pydantic import BaseModel, Field
import traceback
from resources.model_resource.model_mapping import TokenizerMapping, NonHELMMapping


from workflows.detect_workflow import DetectWorkflow
from workflows.exploit_and_patch_workflow import ExploitAndPatchWorkflow
from workflows.patch_workflow import PatchWorkflow
from workflows.chat_workflow import ChatWorkflow
from utils.websocket_manager import websocket_manager, WebSocketManager

class StartWorkflowInput(BaseModel):
    workflow_name: str = Field(..., description="Name of the workflow to start")
    task_dir: Path = Field(..., description="Directory of the tasks")
    bounty_number: str = Field(..., description="Bounty number associated with the workflow")
    interactive: bool = Field(default=False, description="Whether the workflow is interactive")
    iterations: int = Field(..., gt=0, description="Number of phase iterations")
    model: str = Field(..., description="Name of the model")
    use_helm: bool = Field(..., description="Using HELM vs. Non-Helm")

class MessageInputData(BaseModel):
    message_id: str
    new_input_data: str

class MessageData(BaseModel):
    message_id: str

class UpdateInteractiveModeInput(BaseModel):
    interactive: bool



class Server:
    def __init__(self, websocket_manager: WebSocketManager, workflow_factory: Dict[str, Callable]):
        self.app = FastAPI()
        self.websocket_manager = websocket_manager
        self.workflow_factory = workflow_factory
        self.active_workflows: Dict[str, dict] = {}
        self.should_exit = False

        self.setup_routes()
        self.setup_middleware()
        self.setup_signal_handlers()

    def setup_routes(self):
        self.app.get("/workflow/list")(self.list_workflows)
        self.app.post("/workflow/start")(self.start_workflow)
        self.app.post("/workflow/execute/{workflow_id}")(self.execute_workflow)
        self.app.websocket("/ws/{workflow_id}")(self.websocket_endpoint)
        self.app.post("/workflow/next/{workflow_id}")(self.next_message)
        self.app.post("/workflow/rerun-message/{workflow_id}")(self.rerun_message)
        self.app.post("/workflow/edit-message/{workflow_id}")(self.edit_action_input)
        self.app.post("/workflow/{workflow_id}/interactive")(self.update_interactive_mode)
        self.app.get("/workflow/last-message/{workflow_id}")(self.last_message)
        self.app.get("/workflow/first-message/{workflow_id}")(self.first_message)
        self.app.get("/workflow/{workflow_id}/resources")(self.get_workflow_resources)
        self.app.get("/workflow/allmodels")(self.list_all_models)
        self.app.get("/workflow/helmmodels")(self.list_helm_models)
        self.app.post("/workflow/model-change/{workflow_id}")(self.change_model)

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_signal_handlers(self):
        def handle_signal(signum, frame):
            print("\nShutdown signal received. Cleaning up...")
            self.should_exit = True
            
            try:
                # Try to get the existing event loop
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # If no loop is running, we don't create a new one
                # This avoids issues with atexit handlers
                return
            
            # Schedule the shutdown coroutine
            try:
                loop.create_task(self.shutdown())
            except Exception as e:
                print(f"Error scheduling shutdown: {e}")

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    async def shutdown(self):
        """Gracefully shutdown the server with proper cleanup"""
        # Gather all cleanup tasks
        cleanup_tasks = []
        
        # Clean up all websocket connections
        for workflow_id in list(self.websocket_manager.active_connections.keys()):
            connections = list(self.websocket_manager.active_connections[workflow_id])
            for connection in connections:
                try:
                    cleanup_tasks.append(connection.close())
                except Exception as e:
                    print(f"Error closing connection: {e}")
        
        # Clean up heartbeat tasks
        for task in self.websocket_manager.heartbeat_tasks:
            task.cancel()
            cleanup_tasks.append(task)
        
        # Wait for all cleanup tasks to complete
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                print(f"Error during cleanup: {e}")
        
        # Let the event loop complete any remaining tasks
        try:
            loop = asyncio.get_running_loop()
            loop.stop()
        except Exception as e:
            print(f"Error stopping event loop: {e}")

    async def list_workflows(self):
        return {
            "workflows": [
                {"id": "detect", "name": "Detect Workflow", "description": "Workflow for detecting and exploiting vulnerabilities"},
                {"id": "exploit_and_patch", "name": "Exploit and Patch Workflow", "description": "Workflow for exploiting and patching vulnerabilities"},
                {"id": "patch", "name": "Patch Workflow", "description": "Workflow for patching vulnerabilities"},
                {"id": "chat", "name": "Chat Workflow", "description": "Workflow for chatting"}
            ]
        }

    async def list_all_models(self):
        """List available model types"""
        helm_models = list(set(TokenizerMapping.mapping.keys()))
        nonhelm_models = [value if '/' in value else key for key, value in NonHELMMapping.mapping.items()]
        all_models = sorted(helm_models + nonhelm_models)
        all_models = [{'name': model} for model in all_models]
        return {"allModels": all_models}

    async def list_helm_models(self):
        """List HELM model types"""
        helm_models = sorted(set(TokenizerMapping.mapping.keys()))
        helm_mapping = [{'name': model} for model in helm_models]
        return {"helmModels": helm_mapping}

    async def start_workflow(self, workflow_data: StartWorkflowInput):
        print(workflow_data)
        try:
            workflow = self.workflow_factory[workflow_data.workflow_name](
                task_dir=Path(workflow_data.task_dir),
                bounty_number=workflow_data.bounty_number,
                interactive=workflow_data.interactive,
                phase_iterations=workflow_data.iterations,
                model=workflow_data.model,
                use_helm=workflow_data.use_helm
            )
            
            workflow_id = workflow.workflow_message.workflow_id
            self.active_workflows[workflow_id] = {
                "instance": workflow,
                "status": "initializing"
            }

            return {
                "workflow_id": workflow_id,
                "model": workflow_data.model,
                "status": "initializing"
            }
            
        except Exception as e:
            return {
                "error": str(e)
            }

    async def execute_workflow(self, workflow_id: str):
        """Execute a workflow after WebSocket connection is established"""
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}
        
        try:
            # Start workflow execution in background
            asyncio.create_task(self.run_workflow(workflow_id))
            return {"status": "executing"}
        except Exception as e:
            return {"error": str(e)}

    async def run_workflow(self, workflow_id: str):
        if workflow_id not in self.active_workflows or self.should_exit:
            print(f"Workflow {workflow_id} not found or should exit")
            return
        
        workflow_data = self.active_workflows[workflow_id]
        workflow = workflow_data["instance"]
        
        try:
            workflow_data["status"] = "running"
            await websocket_manager.broadcast(workflow_id, {
                "message_type": "status_update",
                "status": "running"
            })
            
            # Run the workflow
            await workflow.run()

            if not self.should_exit:
                workflow_data["status"] = "completed"
                await websocket_manager.broadcast(workflow_id, {
                    "message_type": "status_update",
                    "status": "completed"
                })
            
        except Exception as e:
            if not self.should_exit:
                print(f"Workflow error: {e}")
                workflow_data["status"] = "error"
                await websocket_manager.broadcast(workflow_id, {
                    "message_type": "status_update",
                    "status": "error",
                    "error": str(e)
                })
                print(f"Broadcasted error status for {workflow_id}")

    async def websocket_endpoint(self, websocket: WebSocket, workflow_id: str):
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
            if workflow_id in self.active_workflows:
                workflow_data = self.active_workflows[workflow_id]
                current_status = workflow_data.get("status", "unknown")
                if current_status not in ["running", "completed"]:
                    print(f"Auto-starting workflow {workflow_id}")
                    asyncio.create_task(self.run_workflow(workflow_id))
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
                asyncio.create_task(self.run_workflow(workflow_id))
                await websocket.send_json({
                    "message_type": "workflow_status",
                    "status": "starting",
                    "can_execute": False
                })
            
            # Handle incoming messages
            while not self.should_exit:
                try:
                    data = await websocket.receive_json()
                    if self.should_exit:
                        break

                    if data.get("type") == "pong":
                        # Heartbeat is handled internally by WebSocketManager
                        continue

                    if data.get("message_type") == "user_message" and workflow_id in self.active_workflows:
                        workflow = self.active_workflows[workflow_id]["instance"]
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

    async def next_iteration(self, workflow_id: str):
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}
        
        workflow = self.active_workflows[workflow_id]["instance"]
        if hasattr(workflow, 'next_iteration_event'):
            workflow.next_iteration_event.set()
            return {"status": "next iteration triggered"}
        else:
            return {"error": "Workflow is not in interactive mode"}

    async def next_message(self, workflow_id: str):
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]
        try:
            result = await workflow.run_next_message()
            if not result:
                result = await self.next_iteration(workflow_id)
                return result  # Return the dictionary directly
                
            print(f"Received result : {result.id}")
            return {"status": "updated", "result": result.id}
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error in next_message: {str(e)}\n{error_traceback}")
            return {"error": str(e), "traceback": error_traceback}

    async def rerun_message(self, workflow_id: str, data: MessageData):
        print(f"Rerunning message: {data.message_id}")
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]

        try:
            result = await workflow.rerun_message(data.message_id)

            return {"status": "updated", "result": result.id}
        except Exception as e:
            error_traceback = traceback.format_exc()
            return {"error": str(e), "traceback": error_traceback}

    async def change_model(self, workflow_id: str, data: dict):
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}
        print(f"Changing Model for Workflow: {workflow_id}, New Name: {data}")
        workflow = self.active_workflows[workflow_id]["instance"]
        try:
            result = await workflow.change_current_model(data['new_model_name'])
            return {"status": "updated", "result": result.id}
        except Exception as e:
            return {"error": str(e)}
    
    async def edit_action_input(self, workflow_id: str, data: MessageInputData):
        print(f"Editing message: {data.message_id}")
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]

        try:
            result = await workflow.edit_one_message(data.message_id, data.new_input_data)
            
            return {"status": "updated", "result": result.id}
        except Exception as e:
            return {"error": str(e)}

    async def update_interactive_mode(self, workflow_id: str, data: UpdateInteractiveModeInput):
        print(f"Received request to update interactive mode for workflow {workflow_id}")
        print(f"Data received: {data}")
        
        try:
            if workflow_id not in self.active_workflows:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            workflow = self.active_workflows[workflow_id]["instance"]
            new_interactive_mode = data.interactive
            
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
        
    async def last_message(self, workflow_id: str):
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}
        
        workflow = self.active_workflows[workflow_id]["instance"]
        last_message_str = await workflow.get_last_message()
        return {
                    "message_type": "last_message",
                    "content": last_message_str
                }

    async def first_message(self, workflow_id: str):
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}
        
        workflow = self.active_workflows[workflow_id]["instance"]
        first_message_str = workflow.initial_prompt
        return {
                    "message_type": "first_message",
                    "content": first_message_str
                }
        
    async def get_workflow_resources(self, workflow_id: str):
        if workflow_id not in self.active_workflows:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow = self.active_workflows[workflow_id]["instance"]
        
        # Implement a method in your workflow class to get the current resources
        resources = workflow.resource_manager.resources
        
        return resources
    
def create_app(ws_manager: WebSocketManager = None, workflow_factory: Dict[str, Callable] = None):
    if ws_manager is None:
        ws_manager = websocket_manager

    if workflow_factory is None:
        workflow_factory = {
            "Detect Workflow": DetectWorkflow,
            "Exploit and Patch Workflow": ExploitAndPatchWorkflow,
            "Patch Workflow": PatchWorkflow,
            "Chat Workflow": ChatWorkflow
        }

    server = Server(ws_manager, workflow_factory)
    return server.app

app = create_app()
            
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)