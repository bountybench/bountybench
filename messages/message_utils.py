import asyncio
from typing import Dict, List

from messages.config import MessageType, set_logging_level, should_log
from messages.message import Message
from utils.logger import get_main_logger
from utils.websocket_manager import websocket_manager

logger = get_main_logger(__name__)

# Set the logging level
set_logging_level(MessageType.AGENT)

# Dict of workflow_id -> Dict of message_id -> Message
message_dict: Dict[str, Dict[str, Message]] = {}


def broadcast_update(messages):
    """Send an update over WebSocket."""
    if not isinstance(messages, list):
        messages = [messages]

    data_list = [msg.to_broadcast_dict() for msg in messages]
    workflow_id = messages[0].workflow_id  # Assumes all messages are for the same workflow

    try:
        loop = asyncio.get_running_loop()

        if not loop.is_running():
            result = asyncio.run(_broadcast_update_async(workflow_id, data_list))
            return result
        else:
            task = asyncio.create_task(_broadcast_update_async(workflow_id, data_list))
            return task
    except Exception as e:
        logger.error(f"Exception: {e}")

async def _broadcast_update_async(workflow_id: str, data_list: List[dict]):
    try:
        await websocket_manager.broadcast(workflow_id, data_list)
    except Exception as e:
        logger.error(f"Exception: {e}")

    
def log_message(message: Message):
    if not message.workflow_id:
        logger.debug(f"No associated workflow for {type(message)} message {message.id}, skipping logging")
        return

    # Initialize dict for new workflows
    if message.workflow_id not in message_dict:
        message_dict[message.workflow_id] = {}

    message_dict[message.workflow_id][message.id] = message

    broadcast_update(message)
    if should_log(message):  
        workflow_id = message.workflow_id
        message_dict[workflow_id][workflow_id].save()

def generate_subtree(message: Message) -> dict:
    """
    This function generates the direct line including and beneath a given message. 
    Returns direct next, not necessarily most recent version
    """
    messages = []
    messages.append(message)
    while message.next and message.next.prev == message:
        message = message.next
        messages.append(message)

    broadcast_update(messages)

    return messages
