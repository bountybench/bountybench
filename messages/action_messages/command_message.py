from typing import Any, Dict, List, Optional

from agents.prompts import STOP_TOKEN
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message_interface import CommandMessageInterface
from messages.parse_message import parse_field


class CommandMessage(CommandMessageInterface, ActionMessage):
    def __init__(
        self,
        resource_id: str,
        message: str,
        additional_metadata: Optional[Dict[str, Any]] = {},
        prev: "ActionMessage" = None,
        attrs: dict = None,
    ) -> None:
        self._message = message
        self._command = self.parse_command()
        super().__init__(resource_id, message, additional_metadata, prev, attrs)

    @property
    def command(self) -> str:
        return self._command

    def parse_command(self) -> List[str]:
        command = parse_field(self._message, "Command:", stop_str=STOP_TOKEN)
        if not command:
            raise Exception(
                "Command is missing from message, cannot be a command message."
            )
        command = command.lstrip().lstrip("*").lstrip()
        return command

    def to_dict(self) -> dict:
        action_dict = self.action_dict()
        action_dict.update({"command": self.command})
        base_dict = super(ActionMessage, self).to_dict()
        action_dict.update(base_dict)
        return action_dict
