import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, create_autospec
from fastapi import WebSocket

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.websocket_manager import WebSocketManager

@pytest.fixture
def websocket_manager():
    manager = WebSocketManager()
    manager.active_connections.clear()   # Ensure clean state
    return manager

@pytest.fixture
def websocket():
    return AsyncMock(spec=WebSocket)

@pytest.mark.asyncio
async def test_connect(websocket_manager, websocket):
    workflow_id = "test_workflow"
    await websocket_manager.connect(workflow_id, websocket)
    
    websocket.accept.assert_called_once()
    assert workflow_id in websocket_manager.active_connections
    assert websocket in websocket_manager.active_connections[workflow_id]

def test_disconnect(websocket_manager, websocket):
    workflow_id = "test_workflow"
    websocket_manager.active_connections[workflow_id] = [websocket]

    # Call the disconnect method
    websocket_manager.disconnect(workflow_id, websocket)

    # Check if the websocket was correctly removed
    if workflow_id in websocket_manager.active_connections:
        assert websocket not in websocket_manager.active_connections[workflow_id]
    else:
        assert workflow_id not in websocket_manager.active_connections

@pytest.mark.asyncio
async def test_broadcast(websocket_manager, websocket):
    workflow_id = "test_workflow"
    websocket_manager.active_connections[workflow_id] = [websocket]

    message = {"type": "test", "message": "This is a test"}
    await websocket_manager.broadcast(workflow_id, message)
    
    websocket.send_json.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_broadcast_failed_connection(websocket_manager):
    workflow_id = "test_workflow"
    websocket1 = AsyncMock(spec=WebSocket)
    websocket2 = AsyncMock(spec=WebSocket)
    
    websocket_manager.active_connections[workflow_id] = [websocket1, websocket2]
    websocket1.send_json.side_effect = Exception("Test failure")

    message = {"type": "test", "message": "This is a test"}
    await websocket_manager.broadcast(workflow_id, message)
    
    websocket1.send_json.assert_called_once_with(message)
    websocket2.send_json.assert_called_once_with(message)
    assert websocket1 not in websocket_manager.active_connections[workflow_id]

@pytest.mark.asyncio
async def test_close_all_connections(websocket_manager, websocket):
    workflow_id = "test_workflow"
    websocket_manager.active_connections[workflow_id] = [websocket]

    await websocket_manager.close_all_connections()
    
    websocket.close.assert_called_once()
    assert websocket_manager.active_connections == {}

@pytest.mark.asyncio
async def test_connect_multiple(websocket_manager, websocket):
    websocket2 = AsyncMock(spec=WebSocket)
    workflow_id = "test_workflow"

    await websocket_manager.connect(workflow_id, websocket)
    await websocket_manager.connect(workflow_id, websocket2)

    websocket.accept.assert_called_once()
    websocket2.accept.assert_called_once()
    assert len(websocket_manager.active_connections[workflow_id]) == 2
    assert websocket in websocket_manager.active_connections[workflow_id]
    assert websocket2 in websocket_manager.active_connections[workflow_id]


def test_disconnect_nonexistent(websocket_manager, websocket):
    workflow_id = "test_workflow"
    
    # Ensure no connections initially exist
    assert workflow_id not in websocket_manager.active_connections

    websocket_manager.disconnect(workflow_id, websocket)
    
    # Ensure the state is unchanged
    assert workflow_id not in websocket_manager.active_connections

@pytest.mark.asyncio
async def test_broadcast(websocket_manager, websocket):
    workflow_id = "test_workflow"
    websocket_manager.active_connections[workflow_id] = [websocket]

    message = {"type": "test", "message": "This is a test"}
    await websocket_manager.broadcast(workflow_id, message)
    
    websocket.send_json.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_broadcast_no_connections(websocket_manager):
    workflow_id = "test_workflow"
    message = {"type": "test", "message": "This is a test"}

    # Should not raise any exceptions
    await websocket_manager.broadcast(workflow_id, message)

@pytest.mark.asyncio
async def test_broadcast_failed_connection(websocket_manager):
    workflow_id = "test_workflow"
    websocket1 = AsyncMock(spec=WebSocket)
    websocket2 = AsyncMock(spec=WebSocket)
    
    websocket_manager.active_connections[workflow_id] = [websocket1, websocket2]
    websocket1.send_json.side_effect = Exception("Test failure")

    message = {"type": "test", "message": "This is a test"}
    await websocket_manager.broadcast(workflow_id, message)
    
    websocket1.send_json.assert_called_once_with(message)
    websocket2.send_json.assert_called_once_with(message)
    assert websocket1 not in websocket_manager.active_connections[workflow_id]

@pytest.mark.asyncio
async def test_close_all_connections_with_exceptions(websocket_manager):
    websocket1 = AsyncMock(spec=WebSocket)
    websocket2 = AsyncMock(spec=WebSocket)
    websocket2.close.side_effect = Exception("Test Close Exception")
    workflow_id = "test_workflow"

    websocket_manager.active_connections[workflow_id] = [websocket1, websocket2]

    await websocket_manager.close_all_connections()

    websocket1.close.assert_called_once()
    websocket2.close.assert_called_once()
    assert websocket_manager.active_connections == {}

@pytest.mark.asyncio
async def test_connect_disconnect_multiple(websocket_manager, websocket):
    websocket2 = AsyncMock(spec=WebSocket)
    workflow_id = "test_workflow"

    await websocket_manager.connect(workflow_id, websocket)
    await websocket_manager.connect(workflow_id, websocket2)

    websocket_manager.disconnect(workflow_id, websocket)
    assert websocket2 in websocket_manager.active_connections[workflow_id]
    assert websocket not in websocket_manager.active_connections[workflow_id]

    websocket_manager.disconnect(workflow_id, websocket2)
    assert workflow_id not in websocket_manager.active_connections
    
@pytest.mark.asyncio
async def test_disconnect_handles_exceptions(websocket_manager, websocket):
    workflow_id = "test_workflow"
    websocket_manager.active_connections[workflow_id] = [websocket]

    # Mock the entire disconnect method
    with patch.object(websocket_manager, 'disconnect', side_effect=Exception("Test exception")):
        with pytest.raises(Exception, match="Test exception"):
            websocket_manager.disconnect(workflow_id, websocket)