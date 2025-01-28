import pytest
import asyncio
from httpx import AsyncClient
from server import create_app
from tests.fakes import (
    FakeWebSocketManager,
    FakeDetectWorkflow,
    FakeExploitAndPatchWorkflow,
    FakePatchWorkflow,
    FakeChatWorkflow
)

@pytest.fixture
async def async_client(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_websocket_initial_state(async_client, fake_workflow_factory):
    """
    Test that upon connecting to the WebSocket, the client receives the initial state.
    """
    # Start a workflow to obtain a workflow_id
    start_payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": 111,
        "interactive": False,
        "iterations": 1
    }
    start_response = await async_client.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    workflow_id = start_data["workflow_id"]

    # Connect to WebSocket
    async with async_client.websocket_connect(f"/ws/{workflow_id}") as websocket:
        # Receive initial state
        data = await websocket.receive_json()
        assert data["message_type"] == "initial_state"
        assert data["status"] == "initializing"

@pytest.mark.asyncio
async def test_websocket_execute_workflow(async_client, fake_workflow_factory):
    """
    Test executing a workflow via WebSocket and receiving status updates.
    """
    # Start a workflow
    start_payload = {
        "workflow_name": "Chat Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": 222,
        "interactive": False,
        "iterations": 2
    }
    start_response = await async_client.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    workflow_id = start_data["workflow_id"]

    # Connect to WebSocket
    async with async_client.websocket_connect(f"/ws/{workflow_id}") as websocket:
        # Receive initial state
        data = await websocket.receive_json()
        assert data["message_type"] == "initial_state"
        assert data["status"] == "initializing"

        # Send 'start_execution' message
        await websocket.send_json({"message_type": "start_execution"})

        # Receive 'status_update' to 'running'
        data = await websocket.receive_json()
        assert data["message_type"] == "status_update"
        assert data["status"] == "running"

        # Simulate workflow completion
        # In FakeWorkflow.run(), there's a sleep of 0.1 seconds
        await asyncio.sleep(0.2)

        # Receive 'status_update' to 'completed'
        data = await websocket.receive_json()
        assert data["message_type"] == "status_update"
        assert data["status"] == "completed"

@pytest.mark.asyncio
async def test_websocket_user_message(async_client, fake_workflow_factory):
    """
    Test sending a user message in interactive mode and receiving a response.
    """
    # Start an interactive workflow
    start_payload = {
        "workflow_name": "Chat Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": 333,
        "interactive": True,
        "iterations": 3
    }
    start_response = await async_client.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    workflow_id = start_data["workflow_id"]

    # Connect to WebSocket
    async with async_client.websocket_connect(f"/ws/{workflow_id}") as websocket:
        # Receive initial state
        data = await websocket.receive_json()
        assert data["message_type"] == "initial_state"
        assert data["status"] == "initializing"

        # Start execution
        await websocket.send_json({"message_type": "start_execution"})

        # Receive 'status_update' to 'running'
        data = await websocket.receive_json()
        assert data["message_type"] == "status_update"
        assert data["status"] == "running"

        # Simulate workflow completion
        await asyncio.sleep(0.2)

        # Receive 'status_update' to 'completed'
        data = await websocket.receive_json()
        assert data["message_type"] == "status_update"
        assert data["status"] == "completed"

        # Send a user message
        await websocket.send_json({"message_type": "user_message", "content": "Hello"})

        # Receive user message response
        data = await websocket.receive_json()
        assert data["message_type"] == "user_message_response"
        assert data["content"] == "Fake user message response."

@pytest.mark.asyncio
async def test_websocket_disconnect(async_client, fake_workflow_factory):
    """
    Test that the server handles WebSocket disconnections gracefully.
    """
    # Start a workflow
    start_payload = {
        "workflow_name": "Patch Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": 444,
        "interactive": False,
        "iterations": 1
    }
    start_response = await async_client.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    workflow_id = start_data["workflow_id"]

    # Connect to WebSocket
    websocket = await async_client.websocket_connect(f"/ws/{workflow_id}")
    try:
        # Receive initial state
        data = await websocket.receive_json()
        assert data["message_type"] == "initial_state"
        assert data["status"] == "initializing"

        # Close the WebSocket connection abruptly
        await websocket.aclose()

        # Attempt to send a message after closing should raise an exception
        with pytest.raises(Exception):
            await websocket.send_json({"message_type": "start_execution"})
    finally:
        await websocket.aclose()

@pytest.mark.asyncio
async def test_websocket_invalid_message(async_client, fake_workflow_factory):
    """
    Test that sending an invalid message type does not crash the server and handles it appropriately.
    """
    # Start a workflow
    start_payload = {
        "workflow_name": "Chat Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": 555,
        "interactive": True,
        "iterations": 2
    }
    start_response = await async_client.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    workflow_id = start_data["workflow_id"]

    # Connect to WebSocket
    async with async_client.websocket_connect(f"/ws/{workflow_id}") as websocket:
        # Receive initial state
        data = await websocket.receive_json()
        assert data["message_type"] == "initial_state"
        assert data["status"] == "initializing"

        # Send an invalid message type
        await websocket.send_json({"message_type": "unknown_type", "content": "Test"})

        # Depending on server implementation, the server might ignore, send an error, or handle it differently.
        # Since the FakeWebSocketManager doesn't implement error responses, we can check that no additional messages are sent.
        # Alternatively, if the server sends an error, adjust the test accordingly.

        # Wait briefly to see if any unexpected messages are received
        try:
            data = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
            # If an unexpected message is received, you can add assertions here
            # For example:
            # assert data["message_type"] == "error"
            # assert "unknown_type" in data["detail"]
            pass  # No action expected in fake setup
        except asyncio.TimeoutError:
            # No message received as expected
            pass

@pytest.mark.asyncio
async def test_websocket_multiple_connections(async_client, fake_workflow_factory):
    """
    Test that multiple WebSocket connections to the same workflow receive broadcast messages.
    """
    # Start a workflow
    start_payload = {
        "workflow_name": "Detect Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": 666,
        "interactive": False,
        "iterations": 1
    }
    start_response = await async_client.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    start_data = start_response.json()
    workflow_id = start_data["workflow_id"]

    # Connect first WebSocket
    websocket1 = await async_client.websocket_connect(f"/ws/{workflow_id}")
    # Connect second WebSocket
    websocket2 = await async_client.websocket_connect(f"/ws/{workflow_id}")

    try:
        # Receive initial states
        data1 = await websocket1.receive_json()
        data2 = await websocket2.receive_json()
        assert data1["message_type"] == "initial_state"
        assert data2["message_type"] == "initial_state"

        # Send 'start_execution' from first WebSocket
        await websocket1.send_json({"message_type": "start_execution"})

        # Both WebSockets should receive 'status_update' to 'running'
        data1 = await websocket1.receive_json()
        data2 = await websocket2.receive_json()
        assert data1["message_type"] == "status_update"
        assert data1["status"] == "running"
        assert data2["message_type"] == "status_update"
        assert data2["status"] == "running"

        # Simulate workflow completion
        await asyncio.sleep(0.2)

        # Both WebSockets should receive 'status_update' to 'completed'
        data1 = await websocket1.receive_json()
        data2 = await websocket2.receive_json()
        assert data1["message_type"] == "status_update"
        assert data1["status"] == "completed"
        assert data2["message_type"] == "status_update"
        assert data2["status"] == "completed"
    finally:
        await websocket1.aclose()
        await websocket2.aclose()

@pytest.mark.asyncio
async def test_websocket_interactive_mode_toggle(async_client, fake_workflow_factory):
    """
    Test toggling the interactive mode of a workflow via HTTP and interacting via WebSocket.
    """
    # Start a workflow with interactive=False
    start_payload = {
        "workflow_name": "Chat Workflow",
        "task_dir": "/path/to/tasks",
        "bounty_number": 777,
        "interactive": False,
        "iterations": 2
    }
    start_response = await async_client.post("/workflow/start", json=start_payload)
    assert start_response.status_code == 200
    workflow_id = start_response.json()["workflow_id"]

    # Update interactive mode to True
    update_payload = {"interactive": True}
    update_response = await async_client.post(f"/workflow/{workflow_id}/interactive", json=update_payload)
    assert update_response.status_code == 200
    update_data = update_response.json()
    assert update_data["status"] == "success"
    assert update_data["interactive"] is True

    # Connect to WebSocket
    async with async_client.websocket_connect(f"/ws/{workflow_id}") as websocket:
        # Receive initial state
        data = await websocket.receive_json()
        assert data["message_type"] == "initial_state"
        assert data["status"] == "initializing"

        # Send 'start_execution' message
        await websocket.send_json({"message_type": "start_execution"})

        # Receive 'status_update' to 'running'
        data = await websocket.receive_json()
        assert data["message_type"] == "status_update"
        assert data["status"] == "running"

        # Simulate workflow completion
        await asyncio.sleep(0.2)

        # Receive 'status_update' to 'completed'
        data = await websocket.receive_json()
        assert data["message_type"] == "status_update"
        assert data["status"] == "completed"

        # Send a user message now that interactive mode is enabled
        await websocket.send_json({"message_type": "user_message", "content": "Hello after toggle"})

        # Receive user message response
        data = await websocket.receive_json()
        assert data["message_type"] == "user_message_response"
        assert data["content"] == "Fake user message response."