from typing import Dict

from messages.message import Message

# Dict of workflow_id -> Dict of message_id -> Message
message_dict: Dict[str, Dict[str, Message]] = {}
