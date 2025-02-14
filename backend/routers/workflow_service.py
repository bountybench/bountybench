import asyncio
import traceback
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from backend.schema import MessageData, MessageInputData, UpdateInteractiveModeInput

workflow_service_router = APIRouter()


@workflow_service_router.post("/workflow/{workflow_id}/next")
async def next_message(workflow_id: str, request: Request):
    active_workflows = request.app.state.active_workflows
    if workflow_id not in active_workflows:
        return {"error": f"Workflow {workflow_id} not found"}

    workflow = active_workflows[workflow_id]["instance"]
    try:
        result = await workflow.run_next_message()
        if not result:
            result = await next_iteration(workflow_id, active_workflows)
            return result

        print(f"Received result : {result.id}")
        return {"status": "updated", "result": result.id}
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error in next_message: {str(e)}\n{error_traceback}")
        return {"error": str(e), "traceback": error_traceback}



@workflow_service_router.post("/workflow/{workflow_id}/stop")
async def stop_workflow(workflow_id: str, request: Request):
    """
    Stops the execution of a running workflow and removes it from active workflows.
    """
    print(f"Attempting to stop workflow {workflow_id}")
    active_workflows = request.app.state.active_workflows
    if workflow_id not in active_workflows:
        print(f"Workflow {workflow_id} not found in active workflows")
        return {"error": f"Workflow {workflow_id} not found"}

    workflow = active_workflows[workflow_id]["instance"]
    
    try:
        print(f"BEFORE STOP - Workflow {workflow_id} status: {active_workflows[workflow_id]['status']}")

        await workflow.stop()
        
        #Update workflow status
        active_workflows[workflow_id]["status"] = "stopped"


        print(f"AFTER STOP - Workflow {workflow_id} status: {active_workflows[workflow_id]['status']}")


        # Notify WebSocket clients about the stop
        websocket_manager = request.app.state.websocket_manager

        await websocket_manager.broadcast(
            workflow_id,
            {"message_type": "workflow_status", "status": "stopped"}
        )
        

        if workflow_id in websocket_manager.get_active_connections():
            print(f"Closing WebSocket connections for workflow {workflow_id}")
            await websocket_manager.disconnect_all(workflow_id)

        await websocket_manager.broadcast(
            workflow_id,
            {"message_type": "workflow_status", "status": "stopped"}
        )

        return {"status": "stopped", "workflow_id": workflow_id}

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error stopping workflow {workflow_id}: {str(e)}\n{error_traceback}")
        return {"error": str(e), "traceback": error_traceback}



@workflow_service_router.post("/workflow/{workflow_id}/rerun-message")
async def rerun_message(workflow_id: str, data: MessageData, request: Request):
    active_workflows = request.app.state.active_workflows
    print(f"Rerunning message: {data.message_id}")
    if workflow_id not in active_workflows:
        return {"error": f"Workflow {workflow_id} not found"}

    workflow = active_workflows[workflow_id]["instance"]

    try:
        result = await workflow.rerun_message(data.message_id)
        if not result:
            result = await next_iteration(workflow_id, active_workflows)
            return result
        return {"status": "updated", "result": result.id}
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error rerunning message {workflow_id}: {str(e)}\n{error_traceback}")
        return {"error": str(e), "traceback": error_traceback}


@workflow_service_router.post("/workflow/{workflow_id}/edit-message")
async def edit_action_input(workflow_id: str, data: MessageInputData, request: Request):
    active_workflows = request.app.state.active_workflows
    print(f"Editing message: {data.message_id}")
    if workflow_id not in active_workflows:
        return {"error": f"Workflow {workflow_id} not found"}

    workflow = active_workflows[workflow_id]["instance"]

    try:
        result = await workflow.edit_and_rerun_message(data.message_id, data.new_input_data)
        if not result:
            result = await next_iteration(workflow_id, active_workflows)
            return result
        return {"status": "updated", "result": result.id}
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error editing and rerunning message {workflow_id}: {str(e)}\n{error_traceback}")
        return {"error": str(e), "traceback": error_traceback}


@workflow_service_router.post("/workflow/{workflow_id}/interactive")
async def update_interactive_mode(
    workflow_id: str, data: UpdateInteractiveModeInput, request: Request
):
    active_workflows = request.app.state.active_workflows
    print(f"Received request to update interactive mode for workflow {workflow_id}")
    print(f"Data received: {data}")

    try:
        if workflow_id not in active_workflows:
            raise HTTPException(status_code=404, detail="Workflow not found")

        workflow = active_workflows[workflow_id]["instance"]
        new_interactive_mode = data.interactive

        if new_interactive_mode is None:
            raise HTTPException(
                status_code=400, detail="Interactive mode not specified"
            )

        print(f"Attempting to set interactive mode to {new_interactive_mode}")
        await workflow.set_interactive_mode(new_interactive_mode)
        print(f"Interactive mode successfully set to {new_interactive_mode}")

        return {"status": "success", "interactive": new_interactive_mode}

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@workflow_service_router.get("/workflow/{workflow_id}/last-message")
async def last_message(workflow_id: str, request: Request):
    active_workflows = request.app.state.active_workflows
    if workflow_id not in active_workflows:
        return {"error": "Workflow not found"}

    workflow = active_workflows[workflow_id]["instance"]
    last_message_str = await workflow.get_last_message()
    return {"message_type": "last_message", "content": last_message_str}


@workflow_service_router.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    request = websocket.scope["app"]
    active_workflows = request.state.active_workflows
    websocket_manager = request.state.websocket_manager
    should_exit = request.state.should_exit
    try:
        await websocket_manager.connect(workflow_id, websocket)
        print(f"WebSocket connected for workflow {workflow_id}")

        await websocket.send_json(
            {
                "message_type": "connection_established",
                "workflow_id": workflow_id,
                "status": "connected",
            }
        )

        if workflow_id in active_workflows:
            workflow_data = active_workflows[workflow_id]
            current_status = workflow_data.get("status", "unknown")

            workflow_message = workflow_data.get("workflow_message")
            if workflow_message and hasattr(workflow_message, "phase_messages"):
                for phase_message in workflow_message.phase_messages:
                    await websocket.send_json(phase_message.to_dict())

            if current_status not in ["running", "completed", "stopped"]:
                print(f"Auto-starting workflow {workflow_id}")
                asyncio.create_task(
                    run_workflow(
                        workflow_id, active_workflows, websocket_manager, should_exit
                    )
                )
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
            # If workflow doesn't exist yet, start it
            print(f"Auto-starting new workflow {workflow_id}")
            asyncio.create_task(
                run_workflow(
                    workflow_id, active_workflows, websocket_manager, should_exit
                )
            )
            await websocket.send_json(
                {
                    "message_type": "workflow_status",
                    "status": "starting",
                    "can_execute": False,
                }
            )

        # Handle incoming messages
        while not should_exit:
            try:
                data = await websocket.receive_json()
                if should_exit:
                    break

                if data.get("type") == "pong":
                    # Heartbeat is handled internally by WebSocketManager
                    continue

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
        await websocket_manager.disconnect(workflow_id, websocket)
        print(f"Cleaned up connection for workflow {workflow_id}")

async def run_workflow(
    workflow_id: str, active_workflows, websocket_manager, should_exit
):
    if workflow_id not in active_workflows or should_exit:
        print(f"Workflow {workflow_id} not found or should exit")
        return

    workflow_data = active_workflows[workflow_id]
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
                {"message_type": "workflow_status", "status": "error", "error": str(e), "traceback": error_traceback},
            )
            print(f"Broadcasted error status for {workflow_id}")


async def next_iteration(workflow_id: str, active_workflows):
    if workflow_id not in active_workflows:
        return {"error": "Workflow not found"}

    workflow = active_workflows[workflow_id]["instance"]
    if hasattr(workflow, "next_iteration_event"):
        workflow.next_iteration_event.set()
        return {"status": "next iteration triggered"}
    else:
        return {"error": "Workflow is not in interactive mode"}

@workflow_service_router.post("/workflow/{workflow_id}/model-change")
async def change_model(workflow_id: str, data: dict, request: Request):
    active_workflows = request.app.state.active_workflows
    if workflow_id not in active_workflows:
        return {"error": f"Workflow {workflow_id} not found"}
    print(f"Changing Model for Workflow: {workflow_id}, New Name: {data}")
    workflow = active_workflows[workflow_id]["instance"]
    try:
        result = await workflow.change_current_model(data["new_model_name"])
        return {"status": "updated", "result": result.id}
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error stopping workflow {workflow_id}: {str(e)}\n{error_traceback}")
        return {"error": str(e), "traceback": error_traceback}

