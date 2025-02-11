import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from unittest import IsolatedAsyncioTestCase

from tests.ui_backend.fake_workflows import (
    FakeDetectWorkflow,
    FakeExploitAndPatchWorkflow,
    FakePatchWorkflow,
    FakeChatWorkflow
)

# Fixture for the FastAPI app and test client
@pytest.fixture(scope="module")
def test_app():
    fake_workflow_factory = {
        "Detect Workflow": FakeDetectWorkflow,
        "Exploit and Patch Workflow": FakeExploitAndPatchWorkflow,
        "Patch Workflow": FakePatchWorkflow,
        "Chat Workflow": FakeChatWorkflow,
    }
    app = create_app(workflow_factory=fake_workflow_factory)
    return app

@pytest.fixture(scope="module")
def client(test_app):
    return TestClient(test_app)

def test_list_workflows(client):
    """Test the /workflow/list endpoint to ensure it returns the correct list of workflows."""
    response = client.get("/workflow/list")
    assert response.status_code == 200, "Expected status code 200"
    data = response.json()
    assert "workflows" in data, "Response should contain 'workflows' key"
    assert isinstance(data["workflows"], list), "'workflows' should be a list"
    assert len(data["workflows"]) == 4, "There should be exactly 4 workflows listed"

    expected_ids = {"detect", "exploit_and_patch", "patch", "chat"}
    returned_ids = {wf["id"] for wf in data["workflows"]}
    assert returned_ids == expected_ids, "Workflow IDs do not match expected IDs"

def test_start_workflow_success(client):
    """Test starting a workflow with valid data."""
    payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "123",
        "interactive": True,
        "iterations": 5,
        "model": 'test/model',
        "use_helm": False
    }
    response = client.post("/workflow/start", json=payload)
    assert response.status_code == 200, "Expected status code 200"
    data = response.json()
    assert "workflow_id" in data, "Response should contain 'workflow_id'"
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "initializing", "Status should be 'initializing'"
    assert data["workflow_id"] == "fake-123", "Workflow ID does not match expected fake ID"

def test_start_workflow_invalid_name(client):
    """Test starting a workflow with an invalid workflow name."""
    payload = {
        "workflow_name": "Unknown Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "123",
        "interactive": True,
        "iterations": 5,
        "model": 'test/model',
        "use_helm": False
    }
    response = client.post("/workflow/start", json=payload)
    assert response.status_code == 200, "Expected status code 200 even on error"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert "Unknown Workflow" in data["error"], "Error message should indicate unknown workflow"

@pytest.fixture
def started_chat_workflow(client):
    """Fixture to create a started chat workflow for testing."""
    payload = {
        "workflow_name": "Chat Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "456",
        "interactive": True,
        "iterations": 2,
        "model": 'test/model',
        "use_helm": False
    }
    response = client.post("/workflow/start", json=payload)
    assert response.status_code == 200
    return response.json()["workflow_id"]

def test_next_message_success(client, started_chat_workflow):
    """Test retrieving the next message in an existing workflow."""
    response = client.post(f"/workflow/{started_chat_workflow}/next")
    assert response.status_code == 200, "Expected status code 200 for next message"
    data = response.json()
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "updated", "Status should be 'updated'"
    assert "result" in data, "Response should contain 'result'"
    assert data["result"] == "fake-message-id", "Result ID does not match expected fake message ID"

def test_next_message_workflow_not_found(client):
    """Test retrieving the next message for a non-existent workflow."""
    response = client.post("/workflow/nonexistent-id/next")
    assert response.status_code == 200, "Expected status code 200 even on error"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert data["error"] == "Workflow nonexistent-id not found", "Error message should indicate workflow not found"

@pytest.fixture
def started_patch_workflow(client):
    """Fixture to create a started patch workflow for testing."""
    payload = {
        "workflow_name": "Patch Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "789",
        "interactive": False,
        "iterations": 1,
        "model": 'test/model',
        "use_helm": False
    }
    response = client.post("/workflow/start", json=payload)
    assert response.status_code == 200
    return response.json()["workflow_id"]

def test_rerun_message_success(client, started_patch_workflow):
    """Test rerunning a message in an existing workflow."""
    payload = {"message_id": "original-message-id"}
    response = client.post(f"/workflow/{started_patch_workflow}/rerun-message", json=payload)
    assert response.status_code == 200, "Expected status code 200 for rerun message"
    data = response.json()
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "updated", "Status should be 'updated'"
    assert "result" in data, "Response should contain 'result'"
    assert data["result"] == "fake-rerun-message-id", "Result ID does not match expected fake rerun message ID"

def test_rerun_message_workflow_not_found(client):
    """Test rerunning a message in a non-existent workflow."""
    payload = {"message_id": "some-id"}
    response = client.post("/workflow/nonexistent-id/rerun-message", json=payload)
    assert response.status_code == 200, "Expected status code 200 even on error"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert data["error"] == "Workflow nonexistent-id not found", "Error message should indicate workflow not found"

@pytest.fixture
def started_detect_workflow(client):
    """Fixture to create a started detect workflow for testing."""
    payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "654",
        "interactive": False,
        "iterations": 2,
        "model": 'test/model',
        "use_helm": False
    }
    response = client.post("/workflow/start", json=payload)
    assert response.status_code == 200
    return response.json()["workflow_id"]

def test_update_interactive_mode_success(client, started_detect_workflow):
    """Test updating the interactive mode of an existing workflow."""
    payload = {"interactive": True}
    response = client.post(f"/workflow/{started_detect_workflow}/interactive", json=payload)
    assert response.status_code == 200, "Expected status code 200 for updating interactive mode"
    data = response.json()
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "success", "Status should be 'success'"
    assert "interactive" in data, "Response should contain 'interactive'"
    assert data["interactive"] is True, "Interactive mode should be updated to True"

def test_update_interactive_mode_missing_field(client, started_detect_workflow):
    """Test updating the interactive mode without providing the required field."""
    payload = {}
    response = client.post(f"/workflow/{started_detect_workflow}/interactive", json=payload)
    assert response.status_code == 422, "Expected status code 422 for missing 'interactive' field"
    data = response.json()
    assert "detail" in data, "Response should contain 'detail' key"
    assert len(data["detail"]) == 1, "There should be one error"
    error = data["detail"][0]
    assert error["type"] == "missing", "Error type should be 'missing'"
    assert error["loc"] == ["body", "interactive"], "Error location should point to 'interactive' field"

def test_last_message_success(client, started_chat_workflow):
    """Test retrieving the last message of an existing workflow."""
    response = client.get(f"/workflow/{started_chat_workflow}/last-message")
    assert response.status_code == 200, "Expected status code 200 for last message"
    data = response.json()
    assert "message_type" in data, "Response should contain 'message_type'"
    assert data["message_type"] == "last_message", "Message type should be 'last_message'"
    assert "content" in data, "Response should contain 'content'"
    assert data["content"] == "This is the last fake message.", "Content does not match expected fake last message"

def test_last_message_workflow_not_found(client):
    """Test retrieving the last message of a non-existent workflow."""
    response = client.get("/workflow/nonexistent-id/last-message")
    assert response.status_code == 200, "Expected status code 200 even on error"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert data["error"] == "Workflow not found", "Error message should indicate workflow not found"

def test_start_workflow_missing_fields(client):
    """Test starting a workflow with missing required fields."""
    payload = {
        "workflow_name": "Detect Workflow",
        # "task_dir" is missing
        "bounty_number": "123",
        "interactive": True,
        "iterations": 5,
        "model": 'test/model',
        "use_helm": False
    }
    response = client.post("/workflow/start", json=payload)
    assert response.status_code == 422, "Expected status code 422 for validation error"
    data = response.json()
    assert "detail" in data, "Response should contain 'detail' key"

def test_update_interactive_mode_invalid_payload(client, started_detect_workflow):
    """Test updating interactive mode with invalid payload data."""
    payload = {"interactive": "random"}
    response = client.post(f"/workflow/{started_detect_workflow}/interactive", json=payload)
    assert response.status_code == 422, "Expected status code 422 for type validation error"
    data = response.json()
    assert len(data['detail']) == 1, "Expected one error in the response"
    error = data['detail'][0]
    assert error['type'] == 'bool_parsing', "Expected error type 'bool_parsing'"
    assert error['loc'] == ['body', 'interactive'], "Error should be located in body.interactive"
    assert "Input should be a valid boolean" in error['msg'], "Error message should indicate invalid boolean"
    assert error['input'] == 'random', "Error should include the invalid input"


def test_workflow_restart_creates_new_workflow(client):
    """
    Test that stopping a workflow does not remove it from active workflows,
    and starting a new workflow creates a new instance with a different ID.
    """
    start_payload = {
        "workflow_name": "Exploit and Patch Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "999",
        "interactive": True,
        "iterations": 3,
        "model": "some_model_name",
        "use_helm": False
    }

    new_payload = {
        "workflow_name": "Exploit and Patch Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "100",
        "interactive": True,
        "iterations": 3,
        "model": "some_model_name",
        "use_helm": False
    }

    # Step 1: Start the first workflow
    start_response_1 = client.post("/workflow/start", json=start_payload)
    assert start_response_1.status_code == 200, "Expected status code 200 for first workflow start"
    workflow_id_1 = start_response_1.json()["workflow_id"]

    # Step 2: Stop the first workflow
    stop_response = client.post(f"/workflow/{workflow_id_1}/stop")
    assert stop_response.status_code == 200, "Expected status code 200 for stopping workflow"
    assert "status" in stop_response.json(), "Response should contain 'status'"
    assert stop_response.json()["status"] == "stopped", "Workflow should be marked as stopped"

    # Step 3: Verify that the stopped workflow still exists in active workflows
    active_workflows_before_restart = client.get("/workflow/active").json()
    found_workflow = next((w for w in active_workflows_before_restart["active_workflows"] if w["id"] == workflow_id_1), None)
    assert found_workflow is not None, "Stopped workflow should still be in active workflows"
    assert found_workflow["status"] == "stopped", "Stopped workflow should have status 'stopped'"

    # Step 4: Start a new workflow
    start_response_2 = client.post("/workflow/start", json=new_payload)
    assert start_response_2.status_code == 200, "Expected status code 200 for second workflow start"
    workflow_id_2 = start_response_2.json()["workflow_id"]

    # Step 5: Ensure the new workflow ID is different
    assert workflow_id_1 != workflow_id_2, "New workflow should have a different ID"

    # Step 6: Ensure both workflows exist in active workflows
    active_workflows_after_restart = client.get("/workflow/active").json()
    workflow_ids = {w["id"] for w in active_workflows_after_restart["active_workflows"]}

    assert workflow_id_1 in workflow_ids, "Old workflow should still exist"
    assert workflow_id_2 in workflow_ids, "New workflow should be added"

    # Step 7: Ensure the old workflow is still stopped and the new workflow is initializing
    old_workflow = next((w for w in active_workflows_after_restart["active_workflows"] if w["id"] == workflow_id_1), None)
    new_workflow = next((w for w in active_workflows_after_restart["active_workflows"] if w["id"] == workflow_id_2), None)

    assert old_workflow["status"] == "stopped", "Old workflow should remain stopped"
    assert new_workflow["status"] == "initializing", "New workflow should be in 'initializing' state"

def test_stopping_multiple_workflows(client):
    """
    Test that stopping multiple workflows correctly updates their statuses to 'stopped'
    while keeping them in active workflows.
    """
    payload_1 = {
        "workflow_name": "Exploit and Patch Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "101",
        "interactive": True,
        "iterations": 3,
        "model": "some_model_name",
        "use_helm": False, 
    }

    payload_2 = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "102",
        "interactive": True,
        "iterations": 3,
        "model": "some_model_name",
        "use_helm": False, 
    }

    
    # Start two workflows
    start_response_1 = client.post("/workflow/start", json=payload_1)
    workflow_id_1 = start_response_1.json()["workflow_id"]

    start_response_2 = client.post("/workflow/start", json=payload_2)
    workflow_id_2 = start_response_2.json()["workflow_id"]

    # Stop both workflows
    stop_response_1 = client.post(f"/workflow/{workflow_id_1}/stop")
    stop_response_2 = client.post(f"/workflow/{workflow_id_2}/stop")

    assert stop_response_1.status_code == 200, "Expected status code 200 for stopping first workflow"
    assert stop_response_2.status_code == 200, "Expected status code 200 for stopping second workflow"

    # Verify that both workflows still exist but are marked as 'stopped'
    active_workflows = client.get("/workflow/active").json()
    workflow_1_status = next(w["status"] for w in active_workflows["active_workflows"] if w["id"] == workflow_id_1)
    workflow_2_status = next(w["status"] for w in active_workflows["active_workflows"] if w["id"] == workflow_id_2)

    assert workflow_1_status == "stopped", "First workflow should be marked as stopped"
    assert workflow_2_status == "stopped", "Second workflow should be marked as stopped"

def test_restarting_workflow_with_same_bounty_number(client):
    """
    Test that stopping a workflow and restarting it with the same bounty number does not overwrite the original workflow.
    """
    payload = {
        "workflow_name": "Exploit and Patch Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "999",
        "interactive": True,
        "iterations": 3,
        "model": "some_model_name",
        "use_helm": False
    }

    # Start the first workflow
    start_response_1 = client.post("/workflow/start", json=payload)
    workflow_id_1 = start_response_1.json()["workflow_id"]

    # Stop the first workflow
    stop_response = client.post(f"/workflow/{workflow_id_1}/stop")
    assert stop_response.status_code == 200, "Expected status code 200 for stopping workflow"

    # Restart with the same bounty number
    start_response_2 = client.post("/workflow/start", json=payload)
    workflow_id_2 = start_response_2.json()["workflow_id"]

    assert workflow_id_1 == workflow_id_2, "New workflow should have same ID with the same bounty number"

def test_stopping_workflow_twice(client):
    """
    Test that stopping a workflow twice does not cause errors and does not change its status after the first stop.
    """
    payload = {
        "workflow_name": "Patch Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "777",
        "interactive": True,
        "iterations": 3,
        "model": "some_model_name",
        "use_helm": False
    }

     # Start the workflow
    start_response = client.post("/workflow/start", json=payload)
    workflow_id = start_response.json()["workflow_id"]

    # Stop the workflow once
    stop_response_1 = client.post(f"/workflow/{workflow_id}/stop")
    assert stop_response_1.status_code == 200, "Expected status code 200 for stopping workflow the first time"
    
    # Stop the workflow again
    stop_response_2 = client.post(f"/workflow/{workflow_id}/stop")
    assert stop_response_2.status_code == 200, "Expected status code 200 even for repeated stop"

    # Verify that the workflow is still present in active workflows with 'stopped' status
    active_workflows = client.get("/workflow/active").json()
    workflow_status = next(w["status"] for w in active_workflows["active_workflows"] if w["id"] == workflow_id)

    assert workflow_status == "stopped", "Workflow should still be in 'stopped' status"

###############################################################################
# ASYNC TESTS
###############################################################################
@pytest.mark.asyncio
async def test_websocket_connection_success(client):
    """Tests connecting to a workflow via websocket."""
    # Setup a known workflow
    start_payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "123",
        "interactive": True,
        "iterations": 5,
        "model": 'test/model',
        "use_helm": False
    }
    start_response = client.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    workflow_id = start_response.json()["workflow_id"]

    with client.websocket_connect(f"/ws/{workflow_id}") as websocket:
        initial_state = websocket.receive_json()
        assert initial_state["message_type"] == "connection_established"
        assert initial_state["status"] == "connected"

@pytest.mark.asyncio
async def test_websocket_receive_status_update(client):
    """Test receiving status updates from the websocket after connection."""
    start_payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": "123",
        "interactive": True,
        "iterations": 5,
        "model": 'test/model',
        "use_helm": False
    }
    start_response = client.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    workflow_id = start_response.json()["workflow_id"]

    with client.websocket_connect(f"/ws/{workflow_id}") as websocket:
        # Verify connection establishment
        connection_msg = websocket.receive_json()
        assert connection_msg["message_type"] == "connection_established"
        assert connection_msg["status"] == "connected"

        # Verify initial status
        status_msg = websocket.receive_json()
        assert status_msg["message_type"] == "workflow_status"
        assert status_msg["status"] == "starting"

        # Verify progression to running state
        running_msg = websocket.receive_json()
        assert running_msg["message_type"] == "workflow_status"
        assert running_msg["status"] == "running"