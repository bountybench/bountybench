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

def broadcast_update(message: Message):
    """Send an update over WebSocket. This can be disabled or customized as desired."""
    data = message.to_dict()
    workflow_id = message.workflow_id
    
    try:
        loop = asyncio.get_running_loop()
        
        if not loop.is_running():
            result = asyncio.run(_broadcast_update_async(workflow_id, data))
            return result
        else:
            task = asyncio.create_task(_broadcast_update_async(workflow_id, data))
            return task
    except Exception as e:
        pass

async def _broadcast_update_async(workflow_id: str, data: dict):
    try:
        await websocket_manager.broadcast(workflow_id, data)
    except Exception as e:
        pass

def log_message(message: Message):
    message_dict[message.id] = message

    broadcast_update(message)

    if should_log(message):  
        workflow_id = message.workflow_id
        message_dict[workflow_id].save()

def update_message(message: Message):
    broadcast_update(message)
    log_message(message)