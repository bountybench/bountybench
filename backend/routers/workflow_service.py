import traceback

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from backend.execution_backends import ExecutionBackend
from backend.schema import MessageData, MessageInputData, UpdateInteractiveModeInput

workflow_service_router = APIRouter()


@workflow_service_router.get("/workflow/{workflow_id}/current")
async def get_workflow_appheader(workflow_id: str, request: Request):
    """
    Get the workflow metadata for AppHeader.
    """
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    result = await execution_backend.get_workflow_appheader(workflow_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


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
    execution_backend: ExecutionBackend = request.app.state.execution_backend
    result = await execution_backend.run_message(workflow_id, data)
    if "error" in result:  # Do not raise an exception
        print(f"Error running message: {result['error']}")
    return result


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
    if "error" in result:  # Do not raise an exception
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
    Toggles the use_mock_model setting using InteractiveController.
    """
    execution_backend: ExecutionBackend = request.app.state.execution_backend

    try:
        data = await request.json()
        new_mock_model_state = data.get("use_mock_model", None)

        if new_mock_model_state is None:
            raise HTTPException(
                status_code=400, detail="use_mock_model value is required"
            )

        result = await execution_backend.update_mock_model_mode(
            workflow_id, new_mock_model_state
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(
            f"Error updating mock model for workflow {workflow_id}: {str(e)}\n{error_traceback}"
        )
        raise HTTPException(status_code=500, detail=str(e))
