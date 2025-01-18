import asyncio

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
    