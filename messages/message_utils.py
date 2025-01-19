import asyncio
import inspect

from messages.message import Message
from messages.config import MessageType, set_logging_level, should_log
from utils.websocket_manager import websocket_manager
from utils.logger import get_main_logger
logger = get_main_logger(__name__)

# Set the logging level
set_logging_level(MessageType.AGENT)

def broadcast_update(workflow_id: str, data: dict):
    """Send an update over WebSocket. This can be disabled or customized as desired."""
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_running():
            return asyncio.run(_broadcast_update_async(workflow_id, data))
        else:
            task = asyncio.create_task(_broadcast_update_async(workflow_id, data))
            task.add_done_callback(lambda t: _handle_broadcast_error(t))
            return task
    except Exception as e:
        logger.error(f"Error in broadcast_update: {e}")

async def _broadcast_update_async(workflow_id: str, data: dict):
        try:
            await websocket_manager.broadcast(workflow_id, data)
        except Exception as e:
            logger.error(f"[WorkflowLogger] Error broadcasting update: {e}")

def _handle_broadcast_error(task):
    try:
        task.result()
    except Exception as e:
        logger.error(f"[WorkflowLogger] Error in broadcast task: {e}")

def log_message(message: Message):
    from messages.workflow_message import WorkflowMessage
    instance = WorkflowMessage.get_instance()

    broadcast_update(instance.workflow_id, message.to_dict())
    if should_log(message):
        instance.save()

async def edit_message(old_message, edit):
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