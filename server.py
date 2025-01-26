from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Dict, Callable
from pathlib import Path
from pydantic import BaseModel
import uvicorn
import signal
import sys

from workflows.detect_workflow import DetectWorkflow
from workflows.exploit_and_patch_workflow import ExploitAndPatchWorkflow
from workflows.patch_workflow import PatchWorkflow
from workflows.chat_workflow import ChatWorkflow
from utils.websocket_manager import WebSocketManager

class MessageInputData(BaseModel):
    message_id: str
    new_input_data: str

class MessageData(BaseModel):
    message_id: str

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

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        print("\nShutdown signal received. Cleaning up...")
        self.should_exit = True
        for workflow_id in list(self.websocket_manager.active_connections.keys()):
            for connection in list(self.websocket_manager.active_connections[workflow_id]):
                try:
                    connection.close()
                except:
                    pass
        sys.exit(0)

    async def list_workflows(self):
        return {
            "workflows": [
                {"id": "detect", "name": "Detect Workflow", "description": "Workflow for detecting and exploiting vulnerabilities"},
                {"id": "exploit_and_patch", "name": "Exploit and Patch Workflow", "description": "Workflow for exploiting and patching vulnerabilities"},
                {"id": "patch", "name": "Patch Workflow", "description": "Workflow for patching vulnerabilities"},
                {"id": "chat", "name": "Chat Workflow", "description": "Workflow for chatting"}
            ]
        }

    async def start_workflow(self, workflow_data: dict):
        try:
            workflow = self.workflow_factory[workflow_data['workflow_name']](
                task_dir=Path(workflow_data['task_dir']),
                bounty_number=workflow_data['bounty_number'],
                interactive=workflow_data.get('interactive', False),
                phase_iterations=int(workflow_data['iterations'])
            )
            
            workflow_id = workflow.workflow_message.workflow_id
            self.active_workflows[workflow_id] = {
                "instance": workflow,
                "status": "initializing"
            }

            return {
                "workflow_id": workflow_id,
                "status": "initializing"
            }
            
        except Exception as e:
            return {
                "error": str(e)
            }

    async def execute_workflow(self, workflow_id: str):
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}
        
        try:
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
            await self.websocket_manager.broadcast(workflow_id, {
                "message_type": "status_update",
                "status": "running"
            })
            
            await workflow.run()

            if not self.should_exit:
                workflow_data["status"] = "completed"
                await self.websocket_manager.broadcast(workflow_id, {
                    "message_type": "status_update",
                    "status": "completed"
                })
            
        except Exception as e:
            if not self.should_exit:
                print(f"Workflow error: {e}")
                workflow_data["status"] = "error"
                await self.websocket_manager.broadcast(workflow_id, {
                    "message_type": "status_update",
                    "status": "error",
                    "error": str(e)
                })

    async def websocket_endpoint(self, websocket: WebSocket, workflow_id: str):
        try:
            await self.websocket_manager.connect(workflow_id, websocket)
            
            if workflow_id in self.active_workflows:
                workflow_data = self.active_workflows[workflow_id]
                await websocket.send_json({
                    "message_type": "initial_state",
                    "status": workflow_data["status"]
                })
            
            while not self.should_exit:
                try:
                    data = await websocket.receive_json()
                    if self.should_exit:
                        break

                    if data.get("message_type") == "user_message" and workflow_id in self.active_workflows:
                        workflow = self.active_workflows[workflow_id]["instance"]
                        if workflow.interactive:
                            result = await workflow.add_user_message(data["content"])
                            await self.websocket_manager.broadcast(workflow_id, {
                                "message_type": "user_message_response",
                                "content": result
                            })

                    elif data.get("message_type") == "start_execution":
                        asyncio.create_task(self.run_workflow(workflow_id))
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    if "disconnect" in str(e).lower():
                        break
                    
        except WebSocketDisconnect:
            print(f"WebSocket disconnected for workflow {workflow_id}")
        except Exception as e:
            print(f"WebSocket error for workflow {workflow_id}: {e}")
        finally:
            self.websocket_manager.disconnect(workflow_id, websocket)

    async def next_message(self, workflow_id: str):
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]
        try:
            result = await workflow.run_next_message()
            if not result:
                result = await self.next_iteration(workflow_id)
                return result
                
            return {"status": "updated", "result": result.id}
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            return {"error": str(e), "traceback": error_traceback}

    async def next_iteration(self, workflow_id: str):
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}
        
        workflow = self.active_workflows[workflow_id]["instance"]
        if hasattr(workflow, 'next_iteration_event'):
            workflow.next_iteration_event.set()
            return {"status": "next iteration triggered"}
        else:
            return {"error": "Workflow is not in interactive mode"}

    async def rerun_message(self, workflow_id: str, data: MessageData):
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]

        try:
            result = await workflow.rerun_message(data.message_id)
            return {"status": "updated", "result": result.id}
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            return {"error": str(e), "traceback": error_traceback}

    async def edit_action_input(self, workflow_id: str, data: MessageInputData):
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]

        try:
            result = await workflow.edit_one_message(data.message_id, data.new_input_data)
            return {"status": "updated", "result": result.id}
        except Exception as e:
            return {"error": str(e)}

    async def update_interactive_mode(self, workflow_id: str, data: dict):
        try:
            if workflow_id not in self.active_workflows:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            workflow = self.active_workflows[workflow_id]["instance"]
            new_interactive_mode = data.get("interactive")
            
            if new_interactive_mode is None:
                raise HTTPException(status_code=400, detail="Interactive mode not specified")
            
            await workflow.set_interactive_mode(new_interactive_mode)
            return {"status": "success", "interactive": new_interactive_mode}
        except Exception as e:
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
        
        resources = workflow.resource_manager.resources
        return resources



def create_app():
    websocket_manager = WebSocketManager()
    workflow_factory = {
        "Detect Workflow": DetectWorkflow,
        "Exploit and Patch Workflow": ExploitAndPatchWorkflow,
        "Patch Workflow": PatchWorkflow,
        "Chat Workflow": ChatWorkflow
    }
    server = Server(websocket_manager, workflow_factory)
    return server.app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)