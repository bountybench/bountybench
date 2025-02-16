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
        additional_metadata: Optional[Dict[str, Any]] = None,
        prev: Optional["ActionMessage"] = None,
    ) -> None:
        super().__init__(resource_id, message, additional_metadata, prev)
        self._command = self._parse_command()

    @property
    def command(self) -> str:
        return self._command

    def _parse_command(self) -> str:
        return extract_command(self.message, STOP_TOKEN)

    def action_dict(self) -> dict:
        action_dict = super().action_dict()
        action_dict["command"] = self.command
        return action_dict
