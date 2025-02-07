import asyncio
from typing import Dict

from messages.config import MessageType, set_logging_level, should_log
from messages.message import Message
from utils.logger import get_main_logger
from utils.websocket_manager import websocket_manager

_message_registry = {}

def register_message_class(cls):
    message_type = cls._get_message_type()
    _message_registry[message_type] = cls

def get_message_class(message_type: str):
    return _message_registry.get(message_type)

logger = get_main_logger(__name__)

# Set the logging level
set_logging_level(MessageType.AGENT)

# Dict of workflow_id -> Dict of message_id -> Message
message_dict: Dict[str, Dict[str, Message]] = {}

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
        logger.error(f"Exception: {e}")


async def _broadcast_update_async(workflow_id: str, data: dict):
    try:
        await websocket_manager.broadcast(workflow_id, data)
    except Exception as e:
        logger.error(f"Exception: {e}")


def register_message(message: Message):
    if message.workflow_id not in message_dict:
        message_dict[message.workflow_id] = {}

    message_dict[message.workflow_id][message.id] = message


def log_message(message: Message):
    if not message.workflow_id:
        logger.debug(
            f"No associated workflow for {type(message)} message {message.id}, skipping logging"
        )
        return

    # Initialize dict for new workflows
    if message.workflow_id not in message_dict:
        message_dict[message.workflow_id] = {}

    message_dict[message.workflow_id][message.id] = message

    broadcast_update(message)
    if should_log(message):
        workflow_id = message.workflow_id
        message_dict[workflow_id][workflow_id].save()
        
def message_from_dict(data: dict) -> Message:
    message_type = data.get('message_type')
    cls = get_message_class(message_type)
    if not cls:
        raise ValueError(f"Unregistered message type: {message_type}")
    return cls.from_dict(data)