import asyncio
from unittest.mock import MagicMock
from fastapi import WebSocketDisconnect
import pytest
from fastapi.testclient import TestClient

from server import create_app
from utils.websocket_manager import WebSocketManager


def test_list_workflows(client_fixture):
    """
    Test the /workflow/list endpoint to ensure it returns the correct list of workflows.
    """
    response = client_fixture.get("/workflow/list")
    assert response.status_code == 200, "Expected status code 200"
    data = response.json()
    assert "workflows" in data, "Response should contain 'workflows' key"
    assert isinstance(data["workflows"], list), "'workflows' should be a list"
    assert len(data["workflows"]) == 4, "There should be exactly 4 workflows listed"
    
    expected_ids = {"detect", "exploit_and_patch", "patch", "chat"}
    returned_ids = {wf["id"] for wf in data["workflows"]}
    assert returned_ids == expected_ids, "Workflow IDs do not match expected IDs"


def test_start_workflow_success(client_fixture):
    """
    Test starting a workflow with valid data.
    """
    payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "123",
        "interactive": True,
        "iterations": 5
    }
    response = client_fixture.post("/workflow/start", json=payload)
    assert response.status_code == 200, "Expected status code 200"
    data = response.json()
    assert "workflow_id" in data, "Response should contain 'workflow_id'"
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "initializing", "Status should be 'initializing'"
    assert data["workflow_id"] == "fake-123", "Workflow ID does not match expected fake ID"

def test_start_workflow_invalid_name(client_fixture):
    """
    Test starting a workflow with an invalid workflow name.
    """
    payload = {
        "workflow_name": "Unknown Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "123",
        "interactive": True,
        "iterations": 5
    }
    response = client_fixture.post("/workflow/start", json=payload)
    assert response.status_code == 200, "Expected status code 200 even on error (as per server.py)"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert "Unknown Workflow" in data["error"], "Error message should indicate unknown workflow"



def test_execute_workflow_success(client_fixture):
    """
    Test executing an existing workflow.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "123",
        "interactive": False,
        "iterations": 3
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200, "Expected status code 200 for start workflow"
    start_data = start_response.json()
    workflow_id = start_data["workflow_id"]
    
    # Execute the workflow
    execute_response = client_fixture.post(f"/workflow/execute/{workflow_id}")
    assert execute_response.status_code == 200, "Expected status code 200 for execute workflow"
    execute_data = execute_response.json()
    assert "status" in execute_data, "Response should contain 'status'"
    assert execute_data["status"] == "executing", "Status should be 'executing'"

def test_execute_workflow_not_found(client_fixture):
    """
    Test executing a non-existent workflow.
    """
    execute_response = client_fixture.post("/workflow/execute/nonexistent-id")
    assert execute_response.status_code == 200, "Expected status code 200 even on error (as per server.py)"
    execute_data = execute_response.json()
    assert "error" in execute_data, "Response should contain 'error' key"
    assert execute_data["error"] == "Workflow not found", "Error message should indicate workflow not found"



def test_next_message_success(client_fixture):
    """
    Test retrieving the next message in an existing workflow.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Chat Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "456",
        "interactive": True,
        "iterations": 2
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200, "Expected status code 200 for start workflow"
    workflow_id = start_response.json()["workflow_id"]
    
    # Invoke next_message
    response = client_fixture.post(f"/workflow/next/{workflow_id}")
    assert response.status_code == 200, "Expected status code 200 for next message"
    data = response.json()
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "updated", "Status should be 'updated'"
    assert "result" in data, "Response should contain 'result'"
    assert data["result"] == "fake-message-id", "Result ID does not match expected fake message ID"

def test_next_message_workflow_not_found(client_fixture):
    """
    Test retrieving the next message for a non-existent workflow.
    """
    response = client_fixture.post("/workflow/next/nonexistent-id")
    assert response.status_code == 200, "Expected status code 200 even on error (as per server.py)"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert data["error"] == "Workflow nonexistent-id not found", "Error message should indicate workflow not found"



def test_rerun_message_success(client_fixture):
    """
    Test rerunning a message in an existing workflow.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Patch Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "789",
        "interactive": False,
        "iterations": 1
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200, "Expected status code 200 for start workflow"
    workflow_id = start_response.json()["workflow_id"]
    
    # Rerun a message
    payload = {"message_id": "original-message-id"}
    response = client_fixture.post(f"/workflow/rerun-message/{workflow_id}", json=payload)
    assert response.status_code == 200, "Expected status code 200 for rerun message"
    data = response.json()
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "updated", "Status should be 'updated'"
    assert "result" in data, "Response should contain 'result'"
    assert data["result"] == "fake-rerun-message-id", "Result ID does not match expected fake rerun message ID"

def test_rerun_message_workflow_not_found(client_fixture):
    """
    Test rerunning a message in a non-existent workflow.
    """
    payload = {"message_id": "some-id"}
    response = client_fixture.post("/workflow/rerun-message/nonexistent-id", json=payload)
    assert response.status_code == 200, "Expected status code 200 even on error (as per server.py)"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert data["error"] == "Workflow nonexistent-id not found", "Error message should indicate workflow not found"



def test_edit_action_input_success(client_fixture):
    """
    Test editing an action input in an existing workflow.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Chat Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "321",
        "interactive": True,
        "iterations": 4
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200, "Expected status code 200 for start workflow"
    workflow_id = start_response.json()["workflow_id"]
    
    # Edit a message
    payload = {
        "message_id": "msg-123",
        "new_input_data": "Updated input data"
    }
    response = client_fixture.post(f"/workflow/edit-message/{workflow_id}", json=payload)
    assert response.status_code == 200, "Expected status code 200 for edit message"
    data = response.json()
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "updated", "Status should be 'updated'"
    assert "result" in data, "Response should contain 'result'"
    assert data["result"] == "fake-edited-message-id", "Result ID does not match expected fake edited message ID"

def test_edit_action_input_workflow_not_found(client_fixture):
    """
    Test editing an action input in a non-existent workflow.
    """
    payload = {
        "message_id": "msg-123",
        "new_input_data": "Updated input data"
    }
    response = client_fixture.post("/workflow/edit-message/nonexistent-id", json=payload)
    assert response.status_code == 200, "Expected status code 200 even on error (as per server.py)"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert data["error"] == "Workflow nonexistent-id not found", "Error message should indicate workflow not found"



def test_update_interactive_mode_success(client_fixture):
    """
    Test updating the interactive mode of an existing workflow.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "654",
        "interactive": False,
        "iterations": 2
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200, "Expected status code 200 for start workflow"
    workflow_id = start_response.json()["workflow_id"]
    
    # Update interactive mode
    payload = {"interactive": True}
    response = client_fixture.post(f"/workflow/{workflow_id}/interactive", json=payload)
    assert response.status_code == 200, "Expected status code 200 for updating interactive mode"
    data = response.json()
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "success", "Status should be 'success'"
    assert "interactive" in data, "Response should contain 'interactive'"
    assert data["interactive"] is True, "Interactive mode should be updated to True"

def test_update_interactive_mode_missing_field(client_fixture):
    """
    Test updating the interactive mode without providing the required field.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "654",
        "interactive": False,
        "iterations": 2
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200, "Expected status code 200 for start workflow"
    workflow_id = start_response.json()["workflow_id"]

    # Missing 'interactive' field
    payload = {}
    response = client_fixture.post(f"/workflow/{workflow_id}/interactive", json=payload)
    assert response.status_code == 422, "Expected status code 422 for missing 'interactive' field"
    data = response.json()
    assert "detail" in data, "Response should contain 'detail' key"
    assert len(data["detail"]) == 1, "There should be one error"
    error = data["detail"][0]
    assert error["type"] == "missing", "Error type should be 'missing'"
    assert error["loc"] == ["body", "interactive"], "Error location should point to 'interactive' field"


def test_last_message_success(client_fixture):
    """
    Test retrieving the last message of an existing workflow.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Chat Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "987",
        "interactive": True,
        "iterations": 3
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200, "Expected status code 200 for start workflow"
    workflow_id = start_response.json()["workflow_id"]
    
    # Get last message
    response = client_fixture.get(f"/workflow/last-message/{workflow_id}")
    assert response.status_code == 200, "Expected status code 200 for last message"
    data = response.json()
    assert "message_type" in data, "Response should contain 'message_type'"
    assert data["message_type"] == "last_message", "Message type should be 'last_message'"
    assert "content" in data, "Response should contain 'content'"
    assert data["content"] == "This is the last fake message.", "Content does not match expected fake last message"

def test_last_message_workflow_not_found(client_fixture):
    """
    Test retrieving the last message of a non-existent workflow.
    """
    response = client_fixture.get("/workflow/last-message/nonexistent-id")
    assert response.status_code == 200, "Expected status code 200 even on error (as per server.py)"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert data["error"] == "Workflow not found", "Error message should indicate workflow not found"


def test_first_message_success(client_fixture):
    """
    Test retrieving the first message of an existing workflow.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Patch Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "852",
        "interactive": False,
        "iterations": 1
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200, "Expected status code 200 for start workflow"
    workflow_id = start_response.json()["workflow_id"]
    
    # Get first message
    response = client_fixture.get(f"/workflow/first-message/{workflow_id}")
    assert response.status_code == 200, "Expected status code 200 for first message"
    data = response.json()
    assert "message_type" in data, "Response should contain 'message_type'"
    assert data["message_type"] == "first_message", "Message type should be 'first_message'"
    assert "content" in data, "Response should contain 'content'"
    assert data["content"] == "This is a fake initial prompt.", "Content does not match expected fake first message"

def test_first_message_workflow_not_found(client_fixture):
    """
    Test retrieving the first message of a non-existent workflow.
    """
    response = client_fixture.get("/workflow/first-message/nonexistent-id")
    assert response.status_code == 200, "Expected status code 200 even on error (as per server.py)"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert data["error"] == "Workflow not found", "Error message should indicate workflow not found"


def test_start_workflow_missing_fields(client_fixture):
    """
    Test starting a workflow with missing required fields.
    """
    payload = {
        "workflow_name": "Detect Workflow",
        # "task_dir" is missing
        "bounty_number": "123",
        "interactive": True,
        "iterations": 5
    }
    response = client_fixture.post("/workflow/start", json=payload)
    assert response.status_code == 422, "Expected status code 422 for validation error"
    data = response.json()
    assert "detail" in data, "Response should contain 'detail' key"

def test_edit_action_input_invalid_payload(client_fixture):
    """
    Test editing an action input with invalid payload data.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Chat Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "321",
        "interactive": True,
        "iterations": 4
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    workflow_id = start_response.json()["workflow_id"]
    
    # Send invalid payload (missing 'new_input_data')
    payload = {
        "message_id": "msg-123"
        # "new_input_data" is missing
    }
    response = client_fixture.post(f"/workflow/edit-message/{workflow_id}", json=payload)
    assert response.status_code == 422, "Expected status code 422 for validation error"
    data = response.json()
    assert "detail" in data, "Response should contain 'detail' key"

def test_update_interactive_mode_invalid_payload(client_fixture):
    """
    Test updating interactive mode with invalid payload data.
    """
    # Start a workflow first
    start_payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "654",
        "interactive": False,
        "iterations": 2
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    workflow_id = start_response.json()["workflow_id"]
    
    # Send invalid payload (non-boolean 'interactive' field)
    payload = {"interactive": "random"}  
    response = client_fixture.post(f"/workflow/{workflow_id}/interactive", json=payload)
    assert response.status_code == 422, "Expected status code 422 for type validation error"
    data = response.json()
    assert len(data['detail']) == 1, "Expected one error in the response"
    error = data['detail'][0]
    assert error['type'] == 'bool_parsing', f"Expected error type 'bool_parsing', got '{error['type']}'"
    assert error['loc'] == ['body', 'interactive'], "Error should be located in body.interactive"
    assert "Input should be a valid boolean" in error['msg'], "Error message should indicate invalid boolean input"
    assert error['input'] == 'random', "Error should include the invalid input"


def test_websocket_connection_success(client_fixture, fake_workflow_factory, fake_websocket_manager):
    # Setup fake workflow instance
    workflow_id = "fake-123"
    fake_workflow_instance = fake_workflow_factory["Detect Workflow"](
        task_dir="/path/to/tasks",
        bounty_number="123",
        interactive=True,
        phase_iterations=5,
    )
    fake_workflow_instance.workflow_id = workflow_id
    fake_workflow_instance.status = "initializing"
    
    # Configure the fake workflow factory to return the fake instance
    fake_workflow_factory["Detect Workflow"].return_value = fake_workflow_instance

    # Start the workflow to ensure it's active
    start_payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "123",
        "interactive": True,
        "iterations": 5
    }
    start_response = client_fixture.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    started_workflow_id = start_response.json()["workflow_id"]
    assert started_workflow_id == workflow_id  # Ensure the workflow ID matches

    # Update the server's active_workflows to include the fake workflow
    app = client_fixture.app
    server = app.router.routes[0].app  # Adjust based on your app's structure
    server.active_workflows = {
        workflow_id: {
            "instance": fake_workflow_instance,
            "status": "initializing"
        }
    }

    # Connect to the WebSocket
    with client_fixture.websocket_connect(f"/ws/{workflow_id}") as websocket:
        # Receive the initial state
        initial_state = websocket.receive_json()
        assert initial_state["message_type"] == "initial_state"
        assert initial_state["status"] == "initializing"

        # Instead of using mock assertions, check if the connection was made
        # This assumes FakeWebSocketManager has a way to check connections
        assert fake_websocket_manager.is_connected(workflow_id)
        
        # If FakeWebSocketManager keeps track of connected websockets, you could also check:
        connected_socket = fake_websocket_manager.get_connection(workflow_id)
        assert connected_socket == websocket