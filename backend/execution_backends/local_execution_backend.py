import asyncio
import os
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List

from fastapi import HTTPException
from fastapi.websockets import WebSocketState

from backend.execution_backends import ExecutionBackend
from backend.schema import (
    MessageData,
    MessageInputData,
    StartWorkflowInput,
    UpdateInteractiveModeInput,
)
from resources.model_resource.services.api_key_service import check_api_key_validity


class LocalExecutionBackend(ExecutionBackend):
    """Local execution backend that runs workflows in the same process."""

    def __init__(self, workflow_factory: Dict[str, Callable], app=None):
        super().__init__(workflow_factory)
        self.app = app
        self.active_workflows = (
            {}
        )  # Store active workflows in memory; this would be app.state.active_workflows in the prev implementation

    async def start_workflow(self, workflow_data: StartWorkflowInput) -> Dict[str, Any]:
        """
        Start a workflow and return the workflow ID, model, and status.
        """
        try:
            workflow_args = {
                "task_dir": Path(workflow_data.task_dir),
                "bounty_number": workflow_data.bounty_number,
                "vulnerability_type": workflow_data.vulnerability_type,
                "interactive": workflow_data.interactive,
                "phase_iterations": workflow_data.iterations,
                "use_helm": workflow_data.use_helm,
                "use_mock_model": workflow_data.use_mock_model,
                "max_input_tokens": workflow_data.max_input_tokens,
                "max_output_tokens": workflow_data.max_output_tokens,
            }

            if workflow_data.model != "":
                workflow_args["model"] = workflow_data.model

            workflow = self.workflow_factory[workflow_data.workflow_name](
                **workflow_args
            )
            workflow_id = workflow.workflow_message.workflow_id
            self.active_workflows[workflow_id] = {
                "instance": workflow,
                "status": "initializing",
                "workflow_message": workflow.workflow_message,
            }
            return {
                "workflow_id": workflow_id,
                "model": workflow_data.model,
                "status": "initializing",
            }
        except Exception as e:
            return {"error": str(e)}

    async def stop_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Stops the execution of a running workflow and removes it from active workflows.
        """
        print(f"Attempting to stop workflow {workflow_id}")
        if workflow_id not in self.active_workflows:
            print(f"Workflow {workflow_id} not found in active workflows")
            return {"error": f"Workflow {workflow_id} not found"}

        workflow_data = self.active_workflows[workflow_id]
        workflow = workflow_data["instance"]

        try:
            print(
                f"BEFORE STOP - Workflow {workflow_id} status: {self.active_workflows[workflow_id]['status']}"
            )

            # Cancel the run_workflow task if it exists
            if "task" in workflow_data:
                task = workflow_data["task"]
                task.cancel()  # Cancel the task
                try:
                    await task  # Await the task to handle cancellation
                except asyncio.CancelledError:
                    print(f"Workflow {workflow_id} task cancelled")

            await workflow.stop()

            # Update workflow status
            self.active_workflows[workflow_id]["status"] = "stopped"

            print(
                f"AFTER STOP - Workflow {workflow_id} status: {self.active_workflows[workflow_id]['status']}"
            )

            # Notify WebSocket clients about the stop
            websocket_manager = self.app.state.websocket_manager

            await websocket_manager.broadcast(
                workflow_id, {"message_type": "workflow_status", "status": "stopped"}
            )

            if workflow_id in websocket_manager.get_active_connections():
                print(f"Closing WebSocket connections for workflow {workflow_id}")
                await websocket_manager.disconnect_all(workflow_id)

            await websocket_manager.broadcast(
                workflow_id, {"message_type": "workflow_status", "status": "stopped"}
            )

            return {"workflow_id": workflow_id, "status": "stopped"}

        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error stopping workflow {workflow_id}: {str(e)}\n{error_traceback}")
            return {"error": str(e), "traceback": error_traceback}

    async def restart_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Restart a previously stopped workflow from where it left off.
        """
        print(f"Attempting to restart workflow {workflow_id}")
        active_workflows = self.active_workflows
        if workflow_id not in active_workflows:
            print(f"Workflow {workflow_id} not found in active workflows")
            return {"error": f"Workflow {workflow_id} not found"}

        print(
            f"BEFORE RESTART - Workflow {workflow_id} status: {active_workflows[workflow_id]['status']}"
        )

        workflow = active_workflows[workflow_id]["instance"]

        try:
            print(f"Restarting workflow {workflow_id}")
            await workflow.restart()
            active_workflows[workflow_id]["status"] = "restarting"

            # Notify WebSocket clients about the stop
            websocket_manager = self.app.state.websocket_manager
            await websocket_manager.broadcast(
                workflow_id, {"message_type": "workflow_status", "status": "restarting"}
            )
            print(f"Broadcasted running status for {workflow_id}")
            return {"workflow_id": workflow_id, "status": "restarting"}

        except Exception as e:
            # Handle errors
            error_traceback = traceback.format_exc()
            print(f"Error stopping workflow {workflow_id}: {str(e)}\n{error_traceback}")
            return {"error": str(e), "traceback": error_traceback}

    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the current status of a workflow.
        """
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        status = self.active_workflows[workflow_id]["status"]
        return {"workflow_id": workflow_id, "status": status}

    async def list_active_workflows(self) -> List[Dict[str, Any]]:
        """
        List all active workflows.
        """
        active_workflows_list = []
        for workflow_id, workflow_data in self.active_workflows.items():
            active_workflows_list.append(
                {
                    "id": workflow_id,
                    "status": workflow_data["status"],
                    "name": workflow_data["instance"].__class__.__name__,
                    "task": workflow_data["instance"].task,
                    "timestamp": getattr(
                        workflow_data["workflow_message"], "timestamp", None
                    ),
                }
            )
        return active_workflows_list

    async def run_message(
        self, workflow_id: str, message_data: MessageData
    ) -> Dict[str, Any]:
        """
        Run a specific message in the workflow.
        """
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]

        try:
            result = await workflow.interactive_controller.run_message(
                message_data.message_id
            )
            if not result:
                await workflow.interactive_controller.set_last_message(
                    message_data.message_id
                )
                num_iter = workflow.interactive_controller.get_num_iteration(
                    message_data.num_iter, message_data.type_iter
                )
                results = []
                for _ in range(num_iter):
                    result = await self._next_iteration(workflow_id)
                    results.append(result)
                return results
            return {"status": "updated", "result": result.id}
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error running message {workflow_id}: {str(e)}\n{error_traceback}")
            return {"error": str(e), "traceback": error_traceback}

    async def edit_message(
        self, workflow_id: str, message_data: MessageInputData
    ) -> Dict[str, Any]:
        """
        Edit and run a message in the workflow.
        """
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]

        try:
            result = await workflow.interactive_controller.edit_and_run_message(
                message_data.message_id, message_data.new_input_data
            )
            if not result:
                await workflow.interactive_controller.set_last_message(
                    message_data.message_id
                )
                result = await self._next_iteration(workflow_id)
                return result
            return {"status": "updated", "result": result.id}
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(
                f"Error editing and running message {workflow_id}: {str(e)}\n{error_traceback}"
            )
            return {"error": str(e), "traceback": error_traceback}

    async def update_interactive_mode(
        self, workflow_id: str, data: UpdateInteractiveModeInput
    ) -> Dict[str, Any]:
        """
        Update the interactive mode of a workflow.
        """
        try:
            if workflow_id not in self.active_workflows:
                return {"error": f"Workflow {workflow_id} not found"}

            workflow = self.active_workflows[workflow_id]["instance"]
            new_interactive_mode: bool = data.interactive

            if new_interactive_mode is None:
                return {"error": "Interactive mode not specified"}

            print(f"Attempting to set interactive mode to {new_interactive_mode}")
            await workflow.interactive_controller.set_interactive_mode(
                new_interactive_mode
            )
            print(f"Interactive mode successfully set to {new_interactive_mode}")

            return {"status": "success", "interactive": new_interactive_mode}
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error updating interactive mode: {str(e)}\n{error_traceback}")
            return {"error": str(e), "traceback": error_traceback}

    async def get_last_message(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the last message from a workflow.
        """
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}

        workflow = self.active_workflows[workflow_id]["instance"]
        last_message_str = await workflow.interactive_controller.get_last_message()
        return {"message_type": "last_message", "content": last_message_str}

    async def handle_websocket_connection(self, workflow_id: str, websocket):
        """
        Handle a WebSocket connection for a workflow.
        """
        websocket_manager = self.app.state.websocket_manager
        should_exit = self.app.state.should_exit

        try:
            print(f"WebSocket connecting for workflow {workflow_id}")
            await websocket_manager.connect(workflow_id, websocket)
            print(f"WebSocket connected for workflow {workflow_id}")

            await websocket.send_json(
                {
                    "message_type": "connection_established",
                    "workflow_id": workflow_id,
                    "status": "connected",
                }
            )

            if workflow_id in self.active_workflows:
                workflow_data = self.active_workflows[workflow_id]
                current_status = workflow_data.get("status", "unknown")

                workflow_message = workflow_data.get("workflow_message")
                if workflow_message and hasattr(workflow_message, "phase_messages"):
                    for phase_message in workflow_message.phase_messages:
                        await websocket.send_json(phase_message.to_broadcast_dict())

                if current_status not in ["running", "completed", "stopped"]:
                    if current_status == "restarting":
                        print(f"Re-starting workflow {workflow_id}")
                        task = asyncio.create_task(
                            self._rerun_workflow(
                                workflow_id, websocket_manager, should_exit
                            )
                        )
                        self.active_workflows[workflow_id]["task"] = task
                    else:
                        print(f"Auto-starting workflow {workflow_id}")
                        task = asyncio.create_task(
                            self._run_workflow(
                                workflow_id, websocket_manager, should_exit
                            )
                        )
                        self.active_workflows[workflow_id]["task"] = task
                        await websocket.send_json(
                            {
                                "message_type": "workflow_status",
                                "status": "starting",
                                "can_execute": False,
                            }
                        )
                else:
                    await websocket.send_json(
                        {
                            "message_type": "workflow_status",
                            "status": current_status,
                            "can_execute": False,
                        }
                    )

            else:
                # If workflow doesn't exist yet, initialize it
                print(f"Auto-starting new workflow {workflow_id}")
                self.active_workflows[workflow_id] = {
                    "status": "initializing",
                }
                task = asyncio.create_task(
                    self._run_workflow(workflow_id, websocket_manager, should_exit)
                )
                self.active_workflows[workflow_id]["task"] = task
                await websocket.send_json(
                    {
                        "message_type": "workflow_status",
                        "status": "starting",
                        "can_execute": False,
                    }
                )

            # Handle incoming messages
            while not should_exit:
                # Check if workflow is still active and not stopped
                if (
                    workflow_id not in self.active_workflows
                    or self.active_workflows[workflow_id].get("status") == "stopped"
                ):
                    print(
                        f"Breaking WebSocket loop - workflow {workflow_id} is stopped or removed"
                    )
                    break

                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                    if should_exit:
                        break

                    if data.get("type") == "pong":
                        # Heartbeat is handled internally by WebSocketManager
                        continue
                except asyncio.TimeoutError:
                    # Timeout is normal, verify client state is not disconnected, continue the loop to check conditions again
                    if websocket.client_state == WebSocketState.DISCONNECTED:
                        print(f"Client disconnected for workflow {workflow_id}")
                        break
                    continue
                except Exception as e:
                    print(f"Error handling WebSocket message: {e}")
                    if (
                        "disconnect" in str(e).lower()
                        or "not connected" in str(e).lower()
                    ):
                        print(
                            f"Connection broken for workflow {workflow_id}, exiting loop"
                        )
                        break

        except Exception as e:
            print(f"WebSocket error for workflow {workflow_id}: {e}")
        finally:
            await websocket_manager.disconnect(workflow_id, websocket)
            print(f"Cleaned up connection for workflow {workflow_id}")

    async def change_model(
        self, workflow_id: str, new_model_name: str
    ) -> Dict[str, Any]:
        """
        Change the model for a workflow.
        """
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]
        try:
            await workflow.interactive_controller.change_current_model(new_model_name)
            return {"status": "updated"}
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(
                f"Error changing model for workflow {workflow_id}: {str(e)}\n{error_traceback}"
            )
            return {"error": str(e), "traceback": error_traceback}

    async def toggle_version(
        self, workflow_id: str, message_id: str, direction: str
    ) -> Dict[str, Any]:
        """
        Toggle between versions of a message.
        """
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]

        try:
            result = await workflow.interactive_controller.toggle_version(
                message_id, direction
            )
            if result:
                return {"status": "updated", "result": result.id}
            return {"error": f"Message {direction} for {message_id} not found"}
        except Exception as e:
            error_traceback = traceback.format_exc()
            return {"error": str(e), "traceback": error_traceback}

    async def get_workflow_resources(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the resources associated with a workflow.
        """
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]
        resource_manager = workflow.resource_manager

        resources = resource_manager.get_resources()
        resource_list = []

        for resource_id, resource in resources.items():
            resource_info = {
                "id": resource_id,
                "type": type(resource).__name__,
                "config": (
                    resource._resource_config.to_dict()
                    if resource._resource_config
                    else None
                ),
            }

            if resource_info["config"] and resource_info["config"].get(
                "use_mock_model"
            ):
                resource_info["config"] = {"use_mock_model": True}

            resource_list.append(resource_info)

        return {"resources": resource_list}

    async def update_mock_model_mode(
        self, workflow_id: str, use_mock_model: bool
    ) -> Dict[str, Any]:
        """
        Update the mock model mode for a workflow.
        """
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow {workflow_id} not found"}

        workflow = self.active_workflows[workflow_id]["instance"]

        try:
            if not use_mock_model:  # User is trying to disable mock mode
                model_name = workflow.params.get("model")
                use_helm = workflow.params.get("use_helm")
                if not check_api_key_validity(model_name, use_helm):
                    raise HTTPException(
                        status_code=403,
                        detail="Cannot disable mock mode: API key is missing or invalid.",
                    )
            await workflow.interactive_controller.set_mock_model(use_mock_model)
            return {"status": "success", "use_mock_model": use_mock_model}
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(
                f"Error updating mock model for workflow {workflow_id}: {str(e)}\n{error_traceback}"
            )
            return {"error": str(e), "traceback": error_traceback}

    async def save_config(self, filename: str, config_content: str) -> Dict[str, Any]:
        """Save configuration to the local filesystem."""
        try:
            # Get the parent directory of the current working directory
            config_dir = Path(os.getcwd()) / "configs"

            # Create the configs directory if it doesn't exist
            config_dir.mkdir(parents=True, exist_ok=True)

            # Create the full file path
            file_path = config_dir / filename

            # Write the configuration to the file
            file_path.write_text(config_content)

            return {"message": f"Configuration saved successfully to {file_path}"}
        except Exception as e:
            return {"error": str(e)}

    async def _run_workflow(self, workflow_id: str, websocket_manager, should_exit):
        """
        Internal method to run a workflow.
        """
        if workflow_id not in self.active_workflows or should_exit:
            print(f"Workflow {workflow_id} not found or should exit")
            return

        workflow_data = self.active_workflows[workflow_id]
        workflow = workflow_data["instance"]

        try:
            # Update status to running after initial start
            workflow_data["status"] = "running"
            await websocket_manager.broadcast(
                workflow_id, {"message_type": "workflow_status", "status": "running"}
            )
            print(f"Broadcasted running status for {workflow_id}")

            print(f"Running workflow {workflow_id}")
            # Run the workflow
            await workflow.run()

            # Handle successful completion
            if not should_exit:
                workflow_data["status"] = "completed"
                await websocket_manager.broadcast(
                    workflow_id,
                    {
                        "message_type": "workflow_status",
                        "status": "completed",
                    },
                )

        except Exception as e:
            error_traceback = traceback.format_exc()
            # Handle errors
            if not should_exit:
                print(f"Workflow error: {e}")
                workflow_data["status"] = "error"
                await websocket_manager.broadcast(
                    workflow_id,
                    {
                        "message_type": "workflow_status",
                        "status": "error",
                        "error": str(e),
                        "traceback": error_traceback,
                    },
                )
                print(f"Broadcasted error status for {workflow_id}")

    async def _rerun_workflow(self, workflow_id: str, websocket_manager, should_exit):
        """
        Internal method to rerun a workflow.
        """
        if workflow_id not in self.active_workflows or should_exit:
            print(f"Workflow {workflow_id} not found or should exit")
            return

        workflow_data = self.active_workflows[workflow_id]
        workflow = workflow_data["instance"]

        try:
            # Update status to running after initial start
            workflow_data["status"] = "running"
            await websocket_manager.broadcast(
                workflow_id, {"message_type": "workflow_status", "status": "running"}
            )
            print(f"Broadcasted running status for {workflow_id}")

            print(f"Running workflow {workflow_id}")
            # Run the workflow
            await workflow.run_restart()

            # Handle successful completion
            if not should_exit:
                workflow_data["status"] = "completed"
                await websocket_manager.broadcast(
                    workflow_id,
                    {
                        "message_type": "workflow_status",
                        "status": "completed",
                    },
                )

        except Exception as e:
            # Handle errors
            if not should_exit:
                print(f"Workflow error: {e}")
                workflow_data["status"] = "error"
                await websocket_manager.broadcast(
                    workflow_id,
                    {
                        "message_type": "workflow_status",
                        "status": "error",
                        "error": str(e),
                    },
                )
                print(f"Broadcasted error status for {workflow_id}")

    async def _next_iteration(self, workflow_id: str) -> Dict[str, Any]:
        """
        Internal method to trigger the next iteration of a workflow.
        """
        print("running next_iteration")
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}

        workflow = self.active_workflows[workflow_id]["instance"]
        if hasattr(workflow, "next_iteration_queue"):
            print("next_iter triggered")
            await workflow.next_iteration_queue.put(1)
            return {"status": "next iteration triggered"}
        else:
            return {"error": "Workflow is not in interactive mode"}
