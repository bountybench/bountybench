from unittest import IsolatedAsyncioTestCase

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from tests.ui_backend.fake_workflows import (
    FakeChatWorkflow,
    FakeDetectPatchWorkflow,
    FakeExploitPatchWorkflow,
    FakePatchWorkflow,
)


# Fixture for the FastAPI app and test client
@pytest.fixture(scope="module")
def test_app():
    fake_workflow_factory = {
        "Detect Workflow": FakeDetectPatchWorkflow,
        "Exploit and Patch Workflow": FakeExploitPatchWorkflow,
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

    expected_ids = {"detect_patch", "exploit_patch", "patch", "chat"}
    returned_ids = {wf["id"] for wf in data["workflows"]}
    assert returned_ids == expected_ids, "Workflow IDs do not match expected IDs"


def test_parallel_run_workflow_success(client):
    """Test starting a workflow with valid data using parallel-run endpoint."""
    payload = {
        "workflow_name": "Detect Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "123"}],
        "models": [{"name": "test/model", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [5],
        "use_mock_model": True,
        "trials_per_config": 1,
    }
    response = client.post("/workflow/parallel-run", json=payload)
    assert response.status_code == 200, "Expected status code 200"
    data = response.json()

    # Check for single workflow response
    if "workflow_id" in data:
        assert "workflow_id" in data, "Response should contain 'workflow_id'"
        assert "status" in data, "Response should contain 'status'"
        assert data["status"] == "initializing", "Status should be 'initializing'"
        assert (
            data["workflow_id"] == "fake-123"
        ), "Workflow ID does not match expected fake ID"
    # Check for multiple workflow response
    else:
        assert "status" in data, "Response should contain 'status'"
        assert data["status"] == "started", "Status should be 'started'"
        assert "workflows" in data, "Response should contain 'workflows'"
        assert len(data["workflows"]) == 1, "Should have 1 workflow started"
        assert (
            data["workflows"][0]["workflow_id"] == "fake-123"
        ), "Workflow ID does not match expected fake ID"


def test_parallel_run_workflow_invalid_name(client):
    """Test starting a workflow with an invalid workflow name using parallel-run endpoint."""
    payload = {
        "workflow_name": "Unknown Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "123"}],
        "models": [{"name": "test/model", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [5],
        "use_mock_model": True,
        "trials_per_config": 1,
    }
    response = client.post("/workflow/parallel-run", json=payload)
    assert response.status_code == 200, "Expected status code 200 even on error"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert (
        "Unknown Workflow" in data["error"]
    ), "Error message should indicate unknown workflow"


@pytest.fixture
def started_chat_workflow(client):
    """Fixture to create a started chat workflow for testing."""
    payload = {
        "workflow_name": "Chat Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "456"}],
        "models": [{"name": "test/model", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [2],
        "use_mock_model": True,
        "trials_per_config": 1,
    }
    response = client.post("/workflow/parallel-run", json=payload)
    assert response.status_code == 200
    data = response.json()
    if "workflow_id" in data:
        return data["workflow_id"]
    else:
        return data["workflows"][0]["workflow_id"]


@pytest.fixture
def started_patch_workflow(client):
    """Fixture to create a started patch workflow for testing."""
    payload = {
        "workflow_name": "Patch Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "789"}],
        "models": [{"name": "test/model", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": False,
        "phase_iterations": [1],
        "use_mock_model": True,
        "trials_per_config": 1,
    }
    response = client.post("/workflow/parallel-run", json=payload)
    assert response.status_code == 200
    data = response.json()
    if "workflow_id" in data:
        return data["workflow_id"]
    else:
        return data["workflows"][0]["workflow_id"]


def test_run_message_success(client, started_patch_workflow):
    """Test running a message in an existing workflow."""
    payload = {"message_id": "original-message-id"}
    response = client.post(
        f"/workflow/{started_patch_workflow}/run-message", json=payload
    )
    assert response.status_code == 200, "Expected status code 200 for run message"
    data = response.json()
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "updated", "Status should be 'updated'"
    assert "result" in data, "Response should contain 'result'"
    assert (
        data["result"] == "fake-run-message-id"
    ), "Result ID does not match expected fake run message ID"


def test_run_message_workflow_not_found(client):
    """Test running a message in a non-existent workflow."""
    payload = {"message_id": "some-id"}
    response = client.post("/workflow/nonexistent-id/run-message", json=payload)
    assert response.status_code == 200, "Expected status code 200 even on error"
    data = response.json()
    assert "error" in data, "Response should contain 'error' key"
    assert (
        data["error"] == "Workflow nonexistent-id not found"
    ), "Error message should indicate workflow not found"


@pytest.fixture
def started_detect_workflow(client):
    """Fixture to create a started detect workflow for testing."""
    payload = {
        "workflow_name": "Detect Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "654"}],
        "models": [{"name": "test/model", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": False,
        "phase_iterations": [2],
        "use_mock_model": True,
        "trials_per_config": 1,
    }
    response = client.post("/workflow/parallel-run", json=payload)
    assert response.status_code == 200
    data = response.json()
    if "workflow_id" in data:
        return data["workflow_id"]
    else:
        return data["workflows"][0]["workflow_id"]


def test_update_interactive_mode_success(client, started_detect_workflow):
    """Test updating the interactive mode of an existing workflow."""
    payload = {"interactive": True}
    response = client.post(
        f"/workflow/{started_detect_workflow}/interactive", json=payload
    )
    assert (
        response.status_code == 200
    ), "Expected status code 200 for updating interactive mode"
    data = response.json()
    assert "status" in data, "Response should contain 'status'"
    assert data["status"] == "success", "Status should be 'success'"
    assert "interactive" in data, "Response should contain 'interactive'"
    assert data["interactive"] is True, "Interactive mode should be updated to True"


def test_parallel_run_workflow_missing_fields(client):
    """Test starting a workflow with missing required fields using parallel-run endpoint."""
    payload = {
        "workflow_name": "Detect Workflow",
        # "tasks" is missing
        "models": [{"name": "test/model", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [5],
        "use_mock_model": True,
        "trials_per_config": 1,
    }
    response = client.post("/workflow/parallel-run", json=payload)
    assert response.status_code == 422, "Expected status code 422 for validation error"
    data = response.json()
    assert "detail" in data, "Response should contain 'detail' key"


def test_workflow_restart_creates_new_workflow(client):
    """
    Test that stopping a workflow does not remove it from active workflows,
    and starting a new workflow creates a new instance with a different ID.
    """
    start_payload = {
        "workflow_name": "Exploit and Patch Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "999"}],
        "models": [{"name": "some_model_name", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [3],
        "use_mock_model": True,
        "trials_per_config": 1,
    }

    new_payload = {
        "workflow_name": "Exploit and Patch Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "100"}],
        "models": [{"name": "some_model_name", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [3],
        "use_mock_model": True,
        "trials_per_config": 1,
    }

    # Step 1: Start the first workflow
    start_response_1 = client.post("/workflow/parallel-run", json=start_payload)
    assert (
        start_response_1.status_code == 200
    ), "Expected status code 200 for first workflow start"
    data_1 = start_response_1.json()
    workflow_id_1 = (
        data_1["workflow_id"]
        if "workflow_id" in data_1
        else data_1["workflows"][0]["workflow_id"]
    )

    # Step 2: Stop the first workflow
    stop_response = client.post(f"/workflow/{workflow_id_1}/stop")
    assert (
        stop_response.status_code == 200
    ), "Expected status code 200 for stopping workflow"
    assert "status" in stop_response.json(), "Response should contain 'status'"
    assert (
        stop_response.json()["status"] == "stopped"
    ), "Workflow should be marked as stopped"

    # Step 3: Verify that the stopped workflow still exists in active workflows
    active_workflows_before_restart = client.get("/workflow/active").json()
    found_workflow = next(
        (
            w
            for w in active_workflows_before_restart["active_workflows"]
            if w["id"] == workflow_id_1
        ),
        None,
    )
    assert (
        found_workflow is not None
    ), "Stopped workflow should still be in active workflows"
    assert (
        found_workflow["status"] == "stopped"
    ), "Stopped workflow should have status 'stopped'"

    # Step 4: Start a new workflow
    start_response_2 = client.post("/workflow/parallel-run", json=new_payload)
    assert (
        start_response_2.status_code == 200
    ), "Expected status code 200 for second workflow start"
    data_2 = start_response_2.json()
    workflow_id_2 = (
        data_2["workflow_id"]
        if "workflow_id" in data_2
        else data_2["workflows"][0]["workflow_id"]
    )

    # Step 5: Ensure the new workflow ID is different
    assert workflow_id_1 != workflow_id_2, "New workflow should have a different ID"

    # Step 6: Ensure both workflows exist in active workflows
    active_workflows_after_restart = client.get("/workflow/active").json()
    workflow_ids = {w["id"] for w in active_workflows_after_restart["active_workflows"]}

    assert workflow_id_1 in workflow_ids, "Old workflow should still exist"
    assert workflow_id_2 in workflow_ids, "New workflow should be added"

    # Step 7: Ensure the old workflow is still stopped and the new workflow is initializing
    old_workflow = next(
        (
            w
            for w in active_workflows_after_restart["active_workflows"]
            if w["id"] == workflow_id_1
        ),
        None,
    )
    new_workflow = next(
        (
            w
            for w in active_workflows_after_restart["active_workflows"]
            if w["id"] == workflow_id_2
        ),
        None,
    )

    assert old_workflow["status"] == "stopped", "Old workflow should remain stopped"
    assert (
        new_workflow["status"] == "initializing"
    ), "New workflow should be in 'initializing' state"


def test_stopping_multiple_workflows(client):
    """
    Test that stopping multiple workflows correctly updates their statuses to 'stopped'
    while keeping them in active workflows.
    """
    payload_1 = {
        "workflow_name": "Exploit and Patch Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "101"}],
        "models": [{"name": "some_model_name", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [3],
        "use_mock_model": True,
        "trials_per_config": 1,
    }

    payload_2 = {
        "workflow_name": "Detect Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "102"}],
        "models": [{"name": "some_model_name", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [3],
        "use_mock_model": True,
        "trials_per_config": 1,
    }

    # Start two workflows
    start_response_1 = client.post("/workflow/parallel-run", json=payload_1)
    data_1 = start_response_1.json()
    workflow_id_1 = (
        data_1["workflow_id"]
        if "workflow_id" in data_1
        else data_1["workflows"][0]["workflow_id"]
    )

    start_response_2 = client.post("/workflow/parallel-run", json=payload_2)
    data_2 = start_response_2.json()
    workflow_id_2 = (
        data_2["workflow_id"]
        if "workflow_id" in data_2
        else data_2["workflows"][0]["workflow_id"]
    )

    # Stop both workflows
    stop_response_1 = client.post(f"/workflow/{workflow_id_1}/stop")
    stop_response_2 = client.post(f"/workflow/{workflow_id_2}/stop")

    assert (
        stop_response_1.status_code == 200
    ), "Expected status code 200 for stopping first workflow"
    assert (
        stop_response_2.status_code == 200
    ), "Expected status code 200 for stopping second workflow"

    # Verify that both workflows still exist but are marked as 'stopped'
    active_workflows = client.get("/workflow/active").json()
    workflow_1_status = next(
        w["status"]
        for w in active_workflows["active_workflows"]
        if w["id"] == workflow_id_1
    )
    workflow_2_status = next(
        w["status"]
        for w in active_workflows["active_workflows"]
        if w["id"] == workflow_id_2
    )

    assert workflow_1_status == "stopped", "First workflow should be marked as stopped"
    assert workflow_2_status == "stopped", "Second workflow should be marked as stopped"


def test_restarting_workflow_with_same_bounty_number(client):
    """
    Test that stopping a workflow and restarting it with the same bounty number does not overwrite the original workflow.
    """
    payload = {
        "workflow_name": "Exploit and Patch Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "999"}],
        "models": [{"name": "some_model_name", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [3],
        "use_mock_model": True,
        "trials_per_config": 1,
    }

    # Start the first workflow
    start_response_1 = client.post("/workflow/parallel-run", json=payload)
    data_1 = start_response_1.json()
    workflow_id_1 = (
        data_1["workflow_id"]
        if "workflow_id" in data_1
        else data_1["workflows"][0]["workflow_id"]
    )

    # Stop the first workflow
    stop_response = client.post(f"/workflow/{workflow_id_1}/stop")
    assert (
        stop_response.status_code == 200
    ), "Expected status code 200 for stopping workflow"

    # Restart with the same bounty number
    start_response_2 = client.post("/workflow/parallel-run", json=payload)
    data_2 = start_response_2.json()
    workflow_id_2 = (
        data_2["workflow_id"]
        if "workflow_id" in data_2
        else data_2["workflows"][0]["workflow_id"]
    )

    assert (
        workflow_id_1 == workflow_id_2
    ), "New workflow should have same ID with the same bounty number"


def test_stopping_workflow_twice(client):
    """
    Test that stopping a workflow twice does not cause errors and does not change its status after the first stop.
    """
    payload = {
        "workflow_name": "Patch Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "777"}],
        "models": [{"name": "some_model_name", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [3],
        "use_mock_model": True,
        "trials_per_config": 1,
    }

    # Start the workflow
    start_response = client.post("/workflow/parallel-run", json=payload)
    data = start_response.json()
    workflow_id = (
        data["workflow_id"]
        if "workflow_id" in data
        else data["workflows"][0]["workflow_id"]
    )

    # Stop the workflow once
    stop_response_1 = client.post(f"/workflow/{workflow_id}/stop")
    assert (
        stop_response_1.status_code == 200
    ), "Expected status code 200 for stopping workflow the first time"

    # Stop the workflow again
    stop_response_2 = client.post(f"/workflow/{workflow_id}/stop")
    assert (
        stop_response_2.status_code == 200
    ), "Expected status code 200 even for repeated stop"

    # Verify that the workflow is still present in active workflows with 'stopped' status
    active_workflows = client.get("/workflow/active").json()
    workflow_status = next(
        w["status"]
        for w in active_workflows["active_workflows"]
        if w["id"] == workflow_id
    )

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
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "123"}],
        "models": [{"name": "test/model", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [5],
        "use_mock_model": True,
        "trials_per_config": 1,
    }
    start_response = client.post("/workflow/parallel-run", json=start_payload)
    assert start_response.status_code == 200
    data = start_response.json()
    workflow_id = (
        data["workflow_id"]
        if "workflow_id" in data
        else data["workflows"][0]["workflow_id"]
    )

    with client.websocket_connect(f"/ws/{workflow_id}") as websocket:
        initial_state = websocket.receive_json()
        assert initial_state["message_type"] == "connection_established"
        assert initial_state["status"] == "connected"


@pytest.mark.asyncio
async def test_websocket_receive_status_update(client):
    """Test receiving status updates from the websocket after connection."""
    start_payload = {
        "workflow_name": "Detect Workflow",
        "tasks": [{"task_dir": "/path/to/tasks", "bounty_number": "123"}],
        "models": [{"name": "test/model", "use_helm": False}],
        "vulnerability_type": "",
        "interactive": True,
        "phase_iterations": [5],
        "use_mock_model": True,
        "trials_per_config": 1,
    }
    start_response = client.post("/workflow/parallel-run", json=start_payload)
    assert start_response.status_code == 200
    data = start_response.json()
    workflow_id = (
        data["workflow_id"]
        if "workflow_id" in data
        else data["workflows"][0]["workflow_id"]
    )

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
