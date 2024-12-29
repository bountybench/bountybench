from typing import Dict, List, Optional, Any
from fastapi import WebSocket
import logging

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
        logger.info(f"New WebSocket connection for workflow {workflow_id}. Total connections: {len(self.active_connections[workflow_id])}")

    def disconnect(self, workflow_id: str, websocket: WebSocket):
        if workflow_id in self.active_connections:
            if websocket in self.active_connections[workflow_id]:
                self.active_connections[workflow_id].remove(websocket)
                logger.info(f"WebSocket disconnected from workflow {workflow_id}. Remaining connections: {len(self.active_connections[workflow_id])}")

    async def broadcast(self, workflow_id: str, message: dict):
        if workflow_id in self.active_connections:
            logger.info(f"Broadcasting to workflow {workflow_id}: {message}")
            for connection in self.active_connections[workflow_id]:
                try:
                    await connection.send_json(message)
                    logger.debug(f"Successfully sent message to a connection in workflow {workflow_id}")
                except Exception as e:
                    logger.error(f"Failed to send message to connection in workflow {workflow_id}: {e}")
                    self.disconnect(workflow_id, connection)
        else:
            logger.warning(f"No active connections for workflow {workflow_id}")

websocket_manager = WebSocketManager()
