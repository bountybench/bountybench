from typing import Any, Dict, Optional

from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message_interface import CommandMessageInterface
from messages.parse_message import extract_command
from prompts.prompts import STOP_TOKEN


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

    @classmethod
    def from_dict(cls, data: dict) -> "CommandMessage":
        """Reconstruct a command message from its dictionary representation"""
        resource_id = data.get("resource_id")
        message = data.get("message", "")
        additional_metadata = data.get("additional_metadata", {})
        command = data.get("command", "")

        # Create the CommandMessage with the extracted data
        action_message = cls(
            resource_id=resource_id,
            message=message,
            additional_metadata=additional_metadata,
        )

        # Set base Message properties
        action_message._id = data.get("current_id")
        action_message.timestamp = data.get("timestamp")

        # Handle prev/next relationships
        if "prev" in data:
            action_message._prev = data.get("prev")
        if "next" in data:
            action_message._next = data.get("next")

        action_message.__class__ = cls  # Set the class to the new class

        if command:
            action_message._command = command
        else:
            # Try to extract command from message
            from messages.convert_message_utils import cast_action_to_command

            try:
                temp_command_message = cast_action_to_command(
                    ActionMessage(
                        resource_id=resource_id,
                        message=message,
                        additional_metadata=additional_metadata,
                    )
                )
                action_message._command = temp_command_message.command
            except Exception:
                # If we can't extract a command, set an empty string
                action_message._command = ""

        return action_message
