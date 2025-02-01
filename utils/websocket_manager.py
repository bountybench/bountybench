from typing import Dict, List, Set
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WebSocketManager:
    _instance = None
    _initialized = False
    HEARTBEAT_INTERVAL = 30  # seconds
    CONNECTION_TIMEOUT = 90  # seconds
    MAX_RETRY_ATTEMPTS = 3

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not WebSocketManager._initialized:
            self.active_connections: Dict[str, List[WebSocket]] = {}
            self.last_heartbeat: Dict[str, Dict[WebSocket, datetime]] = {}
            self.heartbeat_tasks: Set[asyncio.Task] = set()
            self.connection_status: Dict[str, Dict[WebSocket, bool]] = {}
            self.lock = asyncio.Lock()
            WebSocketManager._initialized = True
            logger.info("WebSocket Manager initialized")

    async def connect(self, workflow_id: str, websocket: WebSocket):
        """Connect a new WebSocket client with heartbeat monitoring"""
        try:
            await websocket.accept()
            
            # Initialize workflow-specific dictionaries if needed
            if workflow_id not in self.active_connections:
                self.active_connections[workflow_id] = []
                self.last_heartbeat[workflow_id] = {}
                self.connection_status[workflow_id] = {}
            
            self.active_connections[workflow_id].append(websocket)
            self.last_heartbeat[workflow_id][websocket] = datetime.now()
            self.connection_status[workflow_id][websocket] = True
            
            # Start heartbeat monitoring
            heartbeat_task = asyncio.create_task(
                self._monitor_connection(workflow_id, websocket)
            )
            heartbeat_task.add_done_callback(self.heartbeat_tasks.discard)
            self.heartbeat_tasks.add(heartbeat_task)
            
            logger.info(f"WebSocket connected to workflow {workflow_id}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket connection: {e}")
            await self._handle_connection_error(workflow_id, websocket)
            raise

    async def disconnect(self, workflow_id: str, websocket: WebSocket):
        # Check if connection exists before cleanup
        if not websocket or workflow_id not in self.active_connections:
            return

        try:
            # Check connection state before closing
            if websocket.client_state != 2:  # 2 = ConnectionState.DISCONNECTED
                await websocket.close()
        except Exception as e:
            logger.debug(f"Error closing connection: {str(e)}")
        finally:
            # Atomic cleanup operation
            async with self.lock:
                if workflow_id in self.active_connections:
                    self.active_connections[workflow_id] = [
                        conn for conn in self.active_connections[workflow_id]
                        if conn != websocket
                    ]
                    
                    # Remove empty workflow entries
                    if not self.active_connections[workflow_id]:
                        del self.active_connections[workflow_id]
                        del self.last_heartbeat[workflow_id]
                        del self.connection_status[workflow_id]
                    
                    logger.info(f"WebSocket disconnected from workflow {workflow_id}")
                    
    async def broadcast(self, workflow_id: str, message: dict):
        """Broadcast a message to all connected clients with retry mechanism"""
        if workflow_id not in self.active_connections:
            return

        failed_connections = []
        for connection in self.active_connections[workflow_id][:]:  # Create a copy to iterate
            if not self.connection_status.get(workflow_id, {}).get(connection, False):
                logger.warning(f"Skipping broadcast to inactive connection in workflow {workflow_id}")
                continue

            success = False
            for attempt in range(self.MAX_RETRY_ATTEMPTS):
                try:
                    await connection.send_json(message)
                    success = True
                    break
                except Exception as e:
                    if attempt == self.MAX_RETRY_ATTEMPTS - 1:
                        logger.error(f"Failed to send message after {self.MAX_RETRY_ATTEMPTS} attempts: {e}")
                        failed_connections.append(connection)
                    else:
                        await asyncio.sleep(0.5 * (attempt + 1))

            if not success:
                logger.error(f"Failed to send message to connection in workflow {workflow_id}")

        # Clean up failed connections
        for connection in failed_connections:
            try:
                await self._handle_connection_error(workflow_id, connection)
            except Exception as e:
                logger.error(f"Error handling failed connection: {e}")

    async def _monitor_connection(self, workflow_id: str, websocket: WebSocket):
        try:
            while self.connection_status[workflow_id].get(websocket, False):
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                # Only send ping without timeout checks
                try:
                    await websocket.send_json({"message_type": "ping"})
                except (WebSocketDisconnect, RuntimeError):
                    await self.disconnect(workflow_id, websocket)
                    return

        except asyncio.CancelledError as e:
            logger.info(f"Heartbeat monitor cancelled for workflow {workflow_id}")
            raise e 
        except Exception as e:
            logger.error(f"Error in heartbeat monitor: {e}")
        finally:
            await self._handle_connection_error(workflow_id, websocket)

    async def _handle_connection_error(self, workflow_id: str, websocket: WebSocket):
        """Handle connection errors and cleanup"""
        try:
            if workflow_id in self.connection_status and websocket in self.connection_status[workflow_id]:
                self.connection_status[workflow_id][websocket] = False
            
            try:
                await websocket.close()
            except RuntimeError as e:
                if "close message has been sent" not in str(e):
                    logger.error(f"Error closing websocket: {e}")
            except Exception as e:
                logger.error(f"Unexpected error closing websocket: {e}")
                
        finally:
            await self.disconnect(workflow_id, websocket)

    async def close_all_connections(self):
        """Close all active WebSocket connections and cleanup"""
        logger.info("Closing all WebSocket connections")
        
        # Close all connections
        for workflow_id in list(self.active_connections.keys()):
            for connection in list(self.active_connections[workflow_id]):
                await self._handle_connection_error(workflow_id, connection)
        
        # Cancel all heartbeat tasks
        for task in self.heartbeat_tasks:
            task.cancel()
        
        # Wait for all tasks to complete
        if self.heartbeat_tasks:
            await asyncio.gather(*self.heartbeat_tasks, return_exceptions=True)
        
        # Clear all tracking dictionaries
        self.active_connections.clear()
        self.last_heartbeat.clear()
        self.connection_status.clear()
        self.heartbeat_tasks.clear()
        
        logger.info("All WebSocket connections closed")
    
    def get_active_connections(self):
        """Get dictionary of active connections"""
        return self.active_connections

websocket_manager = WebSocketManager()