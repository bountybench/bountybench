import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class WebSocketConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.state = ConnectionState.DISCONNECTED
        self.last_heartbeat = datetime.now()
        self.retry_count = 0
        self.max_retries = 3
        self._closing = False
        self._closed = False
        self.lock = asyncio.Lock()

    @property
    def is_active(self):
        """Check if the connection is active and can send messages"""
        return (not self._closed and 
                not self._closing and 
                self.state == ConnectionState.CONNECTED)

    async def send_heartbeat(self) -> bool:
        if not self.is_active:
            return False

        try:
            async with self.lock:
                if not self.is_active:  # Double-check after acquiring lock
                    return False
                await self.websocket.send_json({"type": "heartbeat"})
                self.last_heartbeat = datetime.now()
                return True
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
            self.state = ConnectionState.ERROR
            return False

    async def send_json(self, data: dict) -> bool:
        if not self.is_active:
            return False

        try:
            async with self.lock:
                if not self.is_active:  # Double-check after acquiring lock
                    return False
                await self.websocket.send_json(data)
                return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.state = ConnectionState.ERROR
            return False

    async def close(self):
        if self._closed:
            return

        async with self.lock:
            if self._closed:  # Double-check after acquiring lock
                return
            
            self._closing = True
            self.state = ConnectionState.DISCONNECTED
            
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing websocket: {e}")
            finally:
                self._closed = True
                self._closing = False


class WebSocketManager:
    _instance = None
    _initialized = False
    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1  # seconds

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not WebSocketManager._initialized:
            self.active_connections: Dict[str, List[WebSocketConnection]] = {}
            self.message_queue: Dict[str, List[dict]] = {}
            self.heartbeat_tasks: Set[asyncio.Task] = set()
            self.connection_locks: Dict[str, asyncio.Lock] = {}
            WebSocketManager._initialized = True
            logger.info("WebSocket Manager initialized")

    async def start_heartbeat(self, workflow_id: str, connection: WebSocketConnection):
        """Start heartbeat for a connection"""
        while True:
            try:
                if connection.state == ConnectionState.CONNECTED:
                    if not await connection.send_heartbeat():
                        await self._handle_failed_heartbeat(workflow_id, connection)
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                break

    async def _handle_failed_heartbeat(
        self, workflow_id: str, connection: WebSocketConnection
    ):
        """Handle failed heartbeat"""
        logger.warning(f"Failed heartbeat for workflow {workflow_id}")
        if (datetime.now() - connection.last_heartbeat) > timedelta(
            seconds=self.HEARTBEAT_INTERVAL * 2
        ):
            logger.error(f"Connection appears dead for workflow {workflow_id}")
            await self.disconnect(workflow_id, connection.websocket)

    async def connect(self, workflow_id: str, websocket: WebSocket) -> asyncio.Task:
        """Connect a new WebSocket client with improved error handling and race condition prevention"""
        if workflow_id not in self.connection_locks:
            self.connection_locks[workflow_id] = asyncio.Lock()

        connection = None
        heartbeat_task = None

        async with self.connection_locks[workflow_id]:
            try:
                # Initialize data structures before accepting connection
                if workflow_id not in self.active_connections:
                    self.active_connections[workflow_id] = []
                    self.message_queue[workflow_id] = []

                # Accept connection within the lock to prevent race conditions
                await websocket.accept()
                logger.info(f"WebSocket connection accepted for workflow {workflow_id}")
                
                # Initialize and configure connection object atomically
                connection = WebSocketConnection(websocket)
                self.active_connections[workflow_id].append(connection)
                connection.state = ConnectionState.CONNECTED
                
                # Start heartbeat task while still holding the lock
                heartbeat_task = asyncio.create_task(
                    self.start_heartbeat(workflow_id, connection)
                )
                self.heartbeat_tasks.add(heartbeat_task)
                heartbeat_task.add_done_callback(self.heartbeat_tasks.discard)

                # Process queued messages if any exist
                if self.message_queue[workflow_id]:
                    asyncio.create_task(self._process_queued_messages(workflow_id))

                logger.info(f"Connection fully established for workflow {workflow_id}")
                return heartbeat_task

            except Exception as e:
                logger.error(f"Error during WebSocket connection: {e}")
                # Clean up any partially established resources
                if connection and workflow_id in self.active_connections:
                    if connection in self.active_connections[workflow_id]:
                        self.active_connections[workflow_id].remove(connection)
                if heartbeat_task:
                    heartbeat_task.cancel()
                    self.heartbeat_tasks.discard(heartbeat_task)
                try:
                    await websocket.close()
                except Exception as close_error:
                    logger.error(f"Error closing websocket during cleanup: {close_error}")
                raise

    async def disconnect(self, workflow_id: str, websocket: WebSocket):
        """Disconnect a WebSocket client with cleanup"""
        if workflow_id not in self.connection_locks:
            self.connection_locks[workflow_id] = asyncio.Lock()

        async with self.connection_locks[workflow_id]:
            try:
                if workflow_id in self.active_connections:
                    connections = self.active_connections[workflow_id]
                    for conn in connections[:]:  # Create a copy to iterate
                        if conn.websocket == websocket:
                            # Set state before removing from active connections
                            conn.state = ConnectionState.DISCONNECTED
                            connections.remove(conn)
                            # Close connection after removal
                            await conn.close()

                    # Clean up workflow resources if no more connections
                    if not connections:
                        del self.active_connections[workflow_id]
                        if workflow_id in self.message_queue:
                            del self.message_queue[workflow_id]
                        if workflow_id in self.connection_locks:
                            del self.connection_locks[workflow_id]

                    logger.info(f"WebSocket disconnected from workflow {workflow_id}")
            except Exception as e:
                logger.error(f"Error during WebSocket disconnect: {e}")
                # Don't re-raise the exception to ensure cleanup continues

    async def broadcast(self, workflow_id: str, message: dict):
        """Broadcast a message with retry logic and rate limiting"""
        if workflow_id not in self.active_connections:
            # Queue message for later delivery
            if workflow_id not in self.message_queue:
                self.message_queue[workflow_id] = []
            self.message_queue[workflow_id].append(message)
            return

        if workflow_id not in self.connection_locks:
            self.connection_locks[workflow_id] = asyncio.Lock()

        async with self.connection_locks[workflow_id]:
            failed_connections = []
            for connection in self.active_connections[workflow_id]:
                if connection.state != ConnectionState.CONNECTED:
                    continue

                success = False
                for attempt in range(self.MAX_RETRY_ATTEMPTS):
                    try:
                        if await connection.send_json(message):
                            success = True
                            break
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    except Exception as e:
                        logger.error(f"Broadcast attempt {attempt + 1} failed: {e}")
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))

                if not success:
                    failed_connections.append(connection)
                    logger.error(
                        f"Failed to broadcast message after {self.MAX_RETRY_ATTEMPTS} attempts"
                    )

            # Clean up failed connections
            for connection in failed_connections:
                await self.disconnect(workflow_id, connection.websocket)

    async def _process_queued_messages(self, workflow_id: str):
        """Process queued messages for a workflow"""
        if workflow_id in self.message_queue:
            queued_messages = self.message_queue[workflow_id]
            self.message_queue[workflow_id] = []
            for message in queued_messages:
                await self.broadcast(workflow_id, message)

    async def close_all_connections(self):
        """Close all active WebSocket connections with proper cleanup"""
        logger.info("Closing all WebSocket connections")
        # Cancel all heartbeat tasks
        for task in self.heartbeat_tasks:
            task.cancel()

        # Create a copy of workflow_ids to avoid modification during iteration
        workflow_ids = list(self.active_connections.keys())

        for workflow_id in workflow_ids:
            if workflow_id not in self.connection_locks:
                self.connection_locks[workflow_id] = asyncio.Lock()

            async with self.connection_locks[workflow_id]:
                connections = self.active_connections[workflow_id]
                for connection in connections[:]:
                    try:
                        await self.disconnect(workflow_id, connection.websocket)
                    except Exception as e:
                        logger.error(
                            f"Error closing connection for workflow {workflow_id}: {e}"
                        )

        self.active_connections.clear()
        self.message_queue.clear()
        self.connection_locks.clear()
        logger.info("All WebSocket connections closed")


websocket_manager = WebSocketManager()
