from collections import deque
from typing import Dict, List, Optional, Any
from fastapi import WebSocket
import logging
import asyncio

logger = logging.getLogger(__name__)

class WebSocketManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not WebSocketManager._initialized:
            self.active_connections: Dict[str, List[WebSocket]] = {}
            WebSocketManager._initialized = True

            logger.info("WebSocket Manager initialized")

    async def connect(self, workflow_id: str, websocket: WebSocket):
        await websocket.accept()
        if workflow_id not in self.active_connections:
            self.active_connections[workflow_id] = []
        self.active_connections[workflow_id].append(websocket)
        print(f"WebSocket connected for workflow {workflow_id}. Total connections: {len(self.active_connections[workflow_id])}")

    def disconnect(self, workflow_id: str, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        try:
            if workflow_id in self.active_connections:
                if websocket in self.active_connections[workflow_id]:
                    self.active_connections[workflow_id].remove(websocket)
                    logger.info(f"WebSocket disconnected from workflow {workflow_id}. Remaining connections: {len(self.active_connections[workflow_id])}")
                
                # Clean up empty workflow connections
                if not self.active_connections[workflow_id]:
                    del self.active_connections[workflow_id]
                    logger.info(f"Removed empty connection list for workflow {workflow_id}")
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")

    async def broadcast(self, workflow_id: str, message: dict):
        """Broadcast a message to all connected clients for a workflow"""


        print(f"Broadcasting to workflow: {workflow_id}")
        print(f"Active connections: {self.active_connections.keys()}")
        if workflow_id not in self.active_connections:
            print(f"No active connections for workflow {workflow_id}")
            return

        print(f"Broadcasting message type '{message.get('message_type')}' to workflow {workflow_id}")
        failed_connections = []

        for connection in self.active_connections[workflow_id]:
            try:
                await connection.send_json(message)
                print(f"Successfully sent message to a connection in workflow {workflow_id}")
            except Exception as e:
                print(f"Error sending message to connection in workflow {workflow_id}: {e}")
                failed_connections.append(connection)

        # Clean up failed connections
        for connection in failed_connections:
            print(f"Removing failed connection from workflow {workflow_id}")
            self.disconnect(workflow_id, connection)

    async def close_all_connections(self):
        """Close all active WebSocket connections"""
        logger.info("Closing all WebSocket connections")
        for workflow_id in list(self.active_connections.keys()):
            for connection in list(self.active_connections[workflow_id]):
                try:
                    await connection.close()
                    logger.debug(f"Closed connection for workflow {workflow_id}")
                except Exception as e:
                    logger.error(f"Error closing connection for workflow {workflow_id}: {e}")
            self.active_connections[workflow_id] = []
        self.active_connections.clear()
        logger.info("All WebSocket connections closed")


        

websocket_manager = WebSocketManager()
