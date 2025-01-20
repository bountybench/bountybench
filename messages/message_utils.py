import asyncio
import inspect
from typing import Dict

from messages.message import Message
from messages.config import MessageType, set_logging_level, should_log
from utils.websocket_manager import websocket_manager
from messages.workflow_message import WorkflowMessage

from utils.logger import get_main_logger
logger = get_main_logger(__name__)

# Set the logging level
set_logging_level(MessageType.AGENT)

message_dict: Dict[str, Message] = {}

def broadcast_update(workflow_id: str, data: dict):
    """Send an update over WebSocket. This can be disabled or customized as desired."""
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


    from messages.workflow_message import WorkflowMessage
    instance = WorkflowMessage.get_instance()

    broadcast_update(instance.workflow_id, message.to_dict())

    if should_log(message):
        instance.save()

async def edit_message(old_message: Message, edit: str) -> Message:
    while old_message.version_next:
        old_message = old_message.version_next

    dic = old_message.__dict__
    cls = type(old_message)
    init_method = cls.__init__
    signature = inspect.signature(init_method)
    params = {}
    for name, param in signature.parameters.items():
        if "_" + name in dic:
            params[name] = dic["_" + name]

    params['prev'] = None
    params['message'] = edit
    new_message = cls(**params)

    new_message.set_version_prev(old_message)
    new_message.set_next(old_message.next)
    old_message.set_version_next(new_message)


    return new_message

def update_message(message: Message):
    instance = WorkflowMessage.get_instance()
    broadcast_update(instance.workflow_id, message.to_dict())
