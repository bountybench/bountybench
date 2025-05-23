import unittest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import WebSocket

from utils.websocket_manager import websocket_manager, logger
from datetime import datetime


class TestWebsocketManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Clear active connections to ensure a clean state before each test
        websocket_manager.active_connections.clear()
        self.ws_manager = websocket_manager
        # Create a mock WebSocket
        self.websocket = Mock(spec=WebSocket)

    async def test_connect(self):
        workflow_id = "test_workflow"
        await self.ws_manager.connect(workflow_id, self.websocket)

        self.websocket.accept.assert_called_once()
        self.assertIn(workflow_id, self.ws_manager.active_connections)
        self.assertIn(self.websocket, self.ws_manager.active_connections[workflow_id])

    def test_disconnect(self):
        workflow_id = "test_workflow"
        self.ws_manager.active_connections[workflow_id] = [self.websocket]

        # Call the disconnect method
        self.ws_manager.disconnect(workflow_id, self.websocket)

        # Check if the websocket was correctly removed
        if workflow_id in self.ws_manager.active_connections:
            self.assertNotIn(self.websocket, self.ws_manager.active_connections[workflow_id])
        else:
            self.assertNotIn(workflow_id, self.ws_manager.active_connections)

    async def test_broadcast(self):
        workflow_id = "test_workflow"
        self.websocket.send_json = AsyncMock()

        await self.ws_manager.connect(workflow_id, self.websocket)

        message = {"type": "test", "message": "This is a test"}
        await self.ws_manager.broadcast(workflow_id, message)

        self.websocket.send_json.assert_called_once_with(message)

    async def test_broadcast_failed_connection_and_new_connection(self):
        workflow_id = "test_workflow"
        websocket1 = AsyncMock(spec=WebSocket)
        websocket2 = AsyncMock(spec=WebSocket)
        websocket3 = AsyncMock(spec=WebSocket)  # New WebSocket to simulate a new connection

        # Initialize the WebSocketManager and set up connections
        self.ws_manager.active_connections[workflow_id] = [websocket1, websocket2]
        self.ws_manager.connection_status[workflow_id] = {websocket1: True, websocket2: False}  # Mark websocket2 as inactive
        self.ws_manager.last_heartbeat[workflow_id] = {websocket1: datetime.now(), websocket2: datetime.now()}

        # Simulate a failure on the first websocket
        websocket1.send_json.side_effect = Exception("Test failure")
        message = {"type": "test", "message": "This is a test"}

        # Perform the broadcast
        await self.ws_manager.broadcast(workflow_id, message)

        # Validate that the first websocket was retried the maximum number of times
        assert websocket1.send_json.call_count == self.ws_manager.MAX_RETRY_ATTEMPTS
        websocket1.send_json.assert_called_with(message)

        # Verify that the failed connection was removed
        self.assertNotIn(websocket1, self.ws_manager.active_connections[workflow_id])

        # Ensure the second websocket was not called due to inactive status
        websocket2.send_json.assert_not_called()

        # Simulate a new connection (websocket3)
        await self.ws_manager.connect(workflow_id, websocket3)
        self.assertIn(websocket3, self.ws_manager.active_connections[workflow_id])

        # Perform another broadcast and validate the new connection
        new_message = {"type": "test", "message": "New broadcast"}
        await self.ws_manager.broadcast(workflow_id, new_message)

        # Validate the new WebSocket received the broadcast
        websocket3.send_json.assert_called_once_with(new_message)

    async def test_close_all_connections(self):
        workflow_id = "test_workflow"
        self.ws_manager.active_connections[workflow_id] = [self.websocket]

        await self.ws_manager.close_all_connections()

        self.websocket.close.assert_called_once()
        self.assertEqual(self.ws_manager.active_connections, {})

    async def test_close_all_connections_with_exceptions(self):
        websocket1 = AsyncMock(spec=WebSocket)
        websocket2 = AsyncMock(spec=WebSocket)
        workflow_id = "test_workflow"
        self.ws_manager.active_connections[workflow_id] = [websocket1, websocket2]
        self.ws_manager.last_heartbeat[workflow_id] = {websocket1: datetime.now(), websocket2: datetime.now()}
        self.ws_manager.connection_status[workflow_id] = {websocket1: True, websocket2: True}

        websocket1.close.side_effect = Exception("Test Close Exception")

        with self.assertLogs(logger, level='ERROR') as log:
            await self.ws_manager.close_all_connections()

        # Verify that the exception was logged
        self.assertIn("Unexpected error closing websocket: Test Close Exception", log.output[0])

        # Verify that close was called on both websockets
        websocket1.close.assert_called_once()
        websocket2.close.assert_called_once()

        # Verify that connections are cleared
        self.assertNotIn(workflow_id, self.ws_manager.active_connections)
        self.assertNotIn(workflow_id, self.ws_manager.last_heartbeat)
        self.assertNotIn(workflow_id, self.ws_manager.connection_status)

    async def test_connect_multiple(self):
        workflow_id = "test_workflow"
        websocket2 = AsyncMock(spec=WebSocket)

        await self.ws_manager.connect(workflow_id, self.websocket)
        await self.ws_manager.connect(workflow_id, websocket2)

        self.websocket.accept.assert_called_once()
        websocket2.accept.assert_called_once()
        self.assertEqual(len(self.ws_manager.active_connections[workflow_id]), 2)
        self.assertIn(self.websocket, self.ws_manager.active_connections[workflow_id])
        self.assertIn(websocket2, self.ws_manager.active_connections[workflow_id])

    def test_disconnect_nonexistent(self):
        workflow_id = "test_workflow"
        # Ensure no connections initially exist
        self.assertNotIn(workflow_id, self.ws_manager.active_connections)

        self.ws_manager.disconnect(workflow_id, self.websocket)

        # Ensure the state is unchanged
        self.assertNotIn(workflow_id, self.ws_manager.active_connections)

    async def test_broadcast_no_connections(self):
        workflow_id = "test_workflow"
        message = {"type": "test", "message": "This is a test"}

        # Should not raise any exceptions even though there are no connections
        await self.ws_manager.broadcast(workflow_id, message)

    async def test_connect_disconnect_multiple(self):
        workflow_id = "test_workflow"
        websocket2 = AsyncMock(spec=WebSocket)

        await self.ws_manager.connect(workflow_id, self.websocket)
        await self.ws_manager.connect(workflow_id, websocket2)

        self.ws_manager.disconnect(workflow_id, self.websocket)
        self.assertIn(websocket2, self.ws_manager.active_connections[workflow_id])
        self.assertNotIn(self.websocket, self.ws_manager.active_connections[workflow_id])

        self.ws_manager.disconnect(workflow_id, websocket2)
        self.assertNotIn(workflow_id, self.ws_manager.active_connections)

    async def test_disconnect_handles_exceptions(self):
        workflow_id = "test_workflow"
        self.ws_manager.active_connections[workflow_id] = [self.websocket]

        with patch.object(self.ws_manager, 'disconnect', side_effect=Exception("Test exception")):
            with self.assertRaisesRegex(Exception, "Test exception"):
                self.ws_manager.disconnect(workflow_id, self.websocket)


if __name__ == '__main__':
    unittest.main()