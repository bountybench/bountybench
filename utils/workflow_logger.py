import asyncio
from functools import wraps
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.websocket_manager import websocket_manager
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

###############################################################################
# HELPER FUNCTIONS
###############################################################################

def ensure_event_loop():
    """Ensure there's an event loop available in the current thread."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

def run_async(func):
    """Decorator to run async functions from sync code."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = ensure_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper

###############################################################################
# WORKFLOW LOGGER
###############################################################################

@dataclass
class WorkflowMetadata:
    workflow_name: str
    start_time: str
    end_time: Optional[str] = None
    final_status: Optional[str] = None
    additional_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowLog:
    """Holds the basic structure of a workflow log."""
    metadata: WorkflowMetadata
    messages: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # message_id -> message_data
    error_log: List[Dict[str, Any]] = field(default_factory=list)
    agents_used: Dict[str, Any] = field(default_factory=dict)
    resources_used: Dict[str, Any] = field(default_factory=dict)

class WorkflowLogger:
    """A simplified logger for workflows that rely on direct calls from Message objects."""
    
    def __init__(self):
        self._initialized = False
        self._workflow_log: Optional[WorkflowLog] = None
        self._log_file: Optional[Path] = None
        self._workflow_id: Optional[str] = None

    ################################################################
    # INITIALIZATION
    ################################################################
    def initialize(
        self,
        workflow_name: str,
        workflow_id: Optional[str] = None,
        logs_dir: str = "logs",
        task: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the logger with workflow metadata and prepare the log file."""
        if self._initialized:
            # Prevent re-initializing
            return
        
        task = task or {}
        start_time = datetime.now().isoformat()

        # Basic metadata
        metadata = WorkflowMetadata(workflow_name=workflow_name, start_time=start_time)
        self._workflow_log = WorkflowLog(metadata=metadata)

        # Determine the final log filename
        self._workflow_id = workflow_id or f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logs_path = Path(logs_dir)
        logs_path.mkdir(parents=True, exist_ok=True)

        # Build a filename from workflow name + optional task info
        components = [workflow_name]
        for _, value in task.items():
            if value:
                components.append(str(value.name if hasattr(value, "name") else value))

        filename = f"{'_'.join(components)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self._log_file = logs_path / filename

        logger.info(f"[WorkflowLogger] Initialized with ID: {self._workflow_id}")
        self._initialized = True

    @property
    def workflow_id(self) -> Optional[str]:
        return self._workflow_id

    def _ensure_initialized(self):
        if not self._initialized or not self._workflow_log:
            raise RuntimeError("WorkflowLogger is not initialized. Call .initialize() first.")

    ################################################################
    # LOGGING & BROADCASTING
    ################################################################

    def log_message(self, message):
        """
        Core logging method: called by message.log_message(). 
        We'll store the message in an in-memory dict and optionally broadcast.
        """
        self._ensure_initialized()

        # Convert the message to a dictionary. We expect it to have 'id' or a unique key.
        msg_id = getattr(message, 'id', None)
        if not msg_id:
            # Or generate an id if not present.
            msg_id = f"message_{len(self._workflow_log.messages)+1}"

        self._workflow_log.messages[msg_id] = message.to_dict()

        # Optionally broadcast via websocket
        self.broadcast_update({
            "type": "message_update",
            "message_id": msg_id,
            "message_data": message.to_dict()
        })

    def log_error(self, error_msg: str, error_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an error into the workflow's error log."""
        self._ensure_initialized()
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": error_msg,
            **(error_data or {})
        }
        self._workflow_log.error_log.append(error_entry)
        logger.error(f"[WorkflowLogger] {error_msg}")
        # Optionally broadcast
        self.broadcast_update({"type": "error", "details": error_entry})

    def broadcast_update(self, data: dict):
        """Send an update over WebSocket. This can be disabled or customized as desired."""
        try:
            loop = asyncio.get_running_loop()
            if not loop.is_running():
                return asyncio.run(self._broadcast_update_async(data))
            else:
                task = asyncio.create_task(self._broadcast_update_async(data))
                task.add_done_callback(lambda t: self._handle_broadcast_error(t))
                return task
        except Exception as e:
            logger.error(f"Error in broadcast_update: {e}")

    async def _broadcast_update_async(self, data: dict):
        if self._workflow_id:
            try:
                await websocket_manager.broadcast(self._workflow_id, data)
            except Exception as e:
                logger.error(f"[WorkflowLogger] Error broadcasting update: {e}")

    def _handle_broadcast_error(self, task):
        try:
            task.result()
        except Exception as e:
            logger.error(f"[WorkflowLogger] Error in broadcast task: {e}")

    ################################################################
    # RESOURCES & AGENTS
    ################################################################

    def add_agent(self, agent_name: str, agent) -> None:
        """Optionally log agent states."""
        self._ensure_initialized()
        if not hasattr(self._workflow_log, 'agents_used'):
            self._workflow_log.agents_used = {}
        if agent_name not in self._workflow_log.agents_used and hasattr(agent, 'to_dict'):
            self._workflow_log.agents_used[agent_name] = agent.to_dict()

    def add_resource(self, resource_name: str, resource) -> None:
        """Optionally log resource states."""
        self._ensure_initialized()
        if not hasattr(self._workflow_log, 'resources_used'):
            self._workflow_log.resources_used = {}
        if resource_name not in self._workflow_log.resources_used and hasattr(resource, 'to_dict'):
            self._workflow_log.resources_used[resource_name] = resource.to_dict()

    ################################################################
    # METADATA & FINALIZATION
    ################################################################

    def add_metadata(self, key: str, value: Any) -> None:
        """Attach arbitrary metadata to the workflow log."""
        self._ensure_initialized()
        self._workflow_log.metadata.additional_metadata[key] = value

    def finalize(self, final_status: str) -> None:
        """
        Mark the workflow as finished, record the end time and final status,
        then save the log to disk.
        """
        self._ensure_initialized()
        self._workflow_log.metadata.end_time = datetime.now().isoformat()
        self._workflow_log.metadata.final_status = final_status
        self.save_all()

    def save_all(self) -> None:
        """Save the entire in-memory workflow log to JSON file."""
        self._ensure_initialized()
        if not self._log_file:
            raise RuntimeError("No log_file specified. Did you call initialize()?")

        # Build a dictionary of everything
        log_data = {
            "metadata": {
                "workflow_name": self._workflow_log.metadata.workflow_name,
                "start_time": self._workflow_log.metadata.start_time,
                "end_time": self._workflow_log.metadata.end_time,
                "final_status": self._workflow_log.metadata.final_status,
                "additional_metadata": self._workflow_log.metadata.additional_metadata
            },
            "messages": self._workflow_log.messages,
            "error_log": self._workflow_log.error_log,
            "agents_used": self._workflow_log.agents_used,
            "resources_used": self._workflow_log.resources_used
        }

        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._log_file, "w") as f:
            json.dump(log_data, f, indent=4)
        logger.info(f"[WorkflowLogger] Saved log to: {self._log_file}")

workflow_logger = WorkflowLogger()