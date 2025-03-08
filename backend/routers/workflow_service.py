import traceback
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from backend.schema import MessageData, MessageInputData, UpdateInteractiveModeInput
from backend.execution_backends import ExecutionBackend

workflow_service_router = APIRouter()


@workflow_service_router.post("/workflow/{workflow_id}/stop")
async def stop_workflow(workflow_id: str, request: Request):
    """
    Stops the execution of a running workflow and removes it from active workflows.
    """
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    result = await execution_backend.stop_workflow(workflow_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@workflow_service_router.post("/workflow/restart/{workflow_id}")
async def restart_workflow(workflow_id: str, request: Request):
    """
    Restart a previously stopped workflow from where it left off.
    """
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    result = await execution_backend.restart_workflow(workflow_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@workflow_service_router.post("/workflow/{workflow_id}/run-message")
async def run_message(workflow_id: str, data: MessageData, request: Request):
    active_workflows = request.app.state.active_workflows
    print(f"Running message: {data.message_id}")
    if workflow_id not in active_workflows:
        return {"error": f"Workflow {workflow_id} not found"}

    workflow = active_workflows[workflow_id]["instance"]

    try:
        result = await workflow.interactive_controller.run_message(data.message_id)
        if not result:
            await workflow.interactive_controller.set_last_message(data.message_id)
            num_iter = 2
            results = []
            for i in range(num_iter):
                result = await next_iteration(workflow_id, active_workflows)
                results.append(result)
            return results
        return {"status": "updated", "result": result.id}
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error running message {workflow_id}: {str(e)}\n{error_traceback}")
        return {"error": str(e), "traceback": error_traceback}


@workflow_service_router.post("/workflow/{workflow_id}/edit-message")
async def edit_action_input(workflow_id: str, data: MessageInputData, request: Request):
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    result = await execution_backend.edit_message(workflow_id, data)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@workflow_service_router.post("/workflow/{workflow_id}/interactive")
async def update_interactive_mode(
    workflow_id: str, data: UpdateInteractiveModeInput, request: Request
):
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    try:
        result = await execution_backend.update_interactive_mode(workflow_id, data)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@workflow_service_router.get("/workflow/{workflow_id}/last-message")
async def last_message(workflow_id: str, request: Request):
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    result = await execution_backend.get_last_message(workflow_id)
    if "error" in result: # Do not raise an exception
        print(f"Error getting last message: {result['error']}")
    return result


@workflow_service_router.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    request = websocket.scope["app"]
    execution_backend: ExecutionBackend = request.state.execution_backend
    
    try:
        await execution_backend.handle_websocket_connection(workflow_id, websocket)
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
                {
                    "message_type": "workflow_status",
                    "status": "error",
                    "error": str(e),
                    "traceback": error_traceback,
                },
            )
            print(f"Broadcasted error status for {workflow_id}")


async def rerun_workflow(
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
                {"message_type": "workflow_status", "status": "error", "error": str(e)},
            )
            print(f"Broadcasted error status for {workflow_id}")


async def next_iteration(workflow_id: str, active_workflows):
    print("running next_iteration")
    if workflow_id not in active_workflows:
        return {"error": "Workflow not found"}

    workflow = active_workflows[workflow_id]["instance"]
    if hasattr(workflow, "next_iteration_queue"):
        print("next_iter triggered")
        await workflow.next_iteration_queue.put(1)
        return {"status": "next iteration triggered"}
    else:
        return {"error": "Workflow is not in interactive mode"}


@workflow_service_router.post("/workflow/{workflow_id}/model-change")
async def change_model(workflow_id: str, data: dict, request: Request):
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    result = await execution_backend.change_model(workflow_id, data["new_model_name"])
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@workflow_service_router.post("/workflow/{workflow_id}/toggle-version")
async def toggle_version(workflow_id: str, data: dict, request: Request):
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    message_id = data.get("message_id")
    direction = data.get("direction")  # "prev" or "next"
    
    result = await execution_backend.toggle_version(workflow_id, message_id, direction)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@workflow_service_router.get("/workflow/{workflow_id}/resources")
async def get_workflow_resources(workflow_id: str, request: Request):
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    result = await execution_backend.get_workflow_resources(workflow_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@workflow_service_router.post("/workflow/{workflow_id}/mock-model")
async def update_mock_model_mode(workflow_id: str, request: Request):
    """
    Toggles the `use_mock_model` setting using InteractiveController.
    """
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    
    try:
        data = await request.json()
        new_mock_model_state = data.get("use_mock_model", None)

        if new_mock_model_state is None:
            raise HTTPException(status_code=400, detail="use_mock_model value is required")
        
        result = await execution_backend.update_mock_model_mode(workflow_id, new_mock_model_state)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error updating mock model for workflow {workflow_id}: {str(e)}\n{error_traceback}")
        raise HTTPException(status_code=500, detail=str(e))