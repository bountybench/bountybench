import asyncio
from typing import Dict

from messages.message import Message
from messages.config import MessageType, set_logging_level, should_log
from utils.websocket_manager import websocket_manager

from utils.logger import get_main_logger
logger = get_main_logger(__name__)

# Set the logging level
set_logging_level(MessageType.AGENT)

message_dict: Dict[str, Message] = {}

def broadcast_update(data: dict):
    """Send an update over WebSocket. This can be disabled or customized as desired."""
    from messages.workflow_message import WorkflowMessage
    instance = WorkflowMessage.get_instance()
    workflow_id = instance.workflow_id

    print(f"[DEBUG] Entering broadcast_update for workflow_id: {workflow_id}")
    print(f"[DEBUG] Data to broadcast: {data}")
    
    try:
        loop = asyncio.get_running_loop()
        print(f"[DEBUG] Current event loop: {loop}")
        
        if not loop.is_running():
            print("[DEBUG] Loop is not running, calling asyncio.run")
            result = asyncio.run(_broadcast_update_async(workflow_id, data))
            print(f"[DEBUG] asyncio.run completed with result: {result}")
            return result
        else:
            print("[DEBUG] Loop is running, creating task")
            task = asyncio.create_task(_broadcast_update_async(workflow_id, data))
            print(f"[DEBUG] Task created: {task}")
            task.add_done_callback(lambda t: _handle_broadcast_error(t))
            print("[DEBUG] Added error handling callback to task")
            return task
    except Exception as e:
        print(f"[ERROR] Error in broadcast_update: {e}")
        print(f"[ERROR] Failed to broadcast message: {data}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

async def _broadcast_update_async(workflow_id: str, data: dict):
    print(f"[DEBUG] Entering _broadcast_update_async for workflow_id: {workflow_id}")
    try:
        await websocket_manager.broadcast(workflow_id, data)
        print(f"[DEBUG] Successfully broadcasted message for workflow_id: {workflow_id}")
    except Exception as e:
        print(f"[ERROR] Error in _broadcast_update_async: {e}")
        print(f"[ERROR] Failed to broadcast message: {data}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

def _handle_broadcast_error(task):
    print(f"[DEBUG] Entering _handle_broadcast_error for task: {task}")
    try:
        result = task.result()
        print(f"[DEBUG] Task completed successfully with result: {result}")
    except Exception as e:
        print(f"[ERROR] Error in broadcast task: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

def log_message(message: Message):
    message_dict[message.id] = message

    broadcast_update(message.to_dict())

    if should_log(message):  
        from messages.workflow_message import WorkflowMessage
        instance = WorkflowMessage.get_instance()
        instance.save()

def update_message(message: Message):
    broadcast_update(message.to_dict())
    log_message(message)