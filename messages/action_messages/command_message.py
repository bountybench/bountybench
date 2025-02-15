from typing import Any, Dict, Optional

from agents.prompts import STOP_TOKEN
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message_interface import CommandMessageInterface
from messages.parse_message import extract_command


class CommandMessage(CommandMessageInterface, ActionMessage):
    def __init__(
        self,
        resource_id: str,
        message: str,
        additional_metadata: Optional[Dict[str, Any]] = {},
        prev: "ActionMessage" = None,
    ) -> None:
        self._message = message
        self._command = self.parse_command()
        super().__init__(resource_id, message, additional_metadata, prev)

    @property
    def command(self) -> str:
        return self._command

    def parse_command(self) -> str:
        return extract_command(self._message, STOP_TOKEN)

    def _merge_with_action_dict(self) -> dict:
        """Helper to merge action_dict with base_dict and add the answer."""
        base_dict = super().to_base_dict()
        action_dict = self.action_dict()
        action_dict.update({"command": self.command})
        action_dict.update(base_dict)
        return action_dict
    
    def to_broadcast_dict(self) -> dict:
        return self._merge_with_action_dict()

    def to_log_dict(self) -> dict:
        return self._merge_with_action_dict()
