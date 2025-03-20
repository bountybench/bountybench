from typing import Any, Dict, Optional

from messages.message import Message


class ActionMessage(Message):
    def __init__(
        self,
        resource_id: str,
        message: str,
        additional_metadata: Optional[Dict[str, Any]] = {},
        prev: "ActionMessage" = None,
    ) -> None:
        self._resource_id = resource_id
        self._message = message
        self._additional_metadata = additional_metadata
        self._memory = None

        super().__init__(prev)

    @property
    def resource_id(self) -> str:
        return self._resource_id

    @property
    def workflow_id(self) -> str:
        if self.parent:
            return self.parent.workflow_id
        return None

    @property
    def message(self) -> str:
        return self._message

    def set_message(self, value: str):
        """
        Setter for message property.
        """
        self._message = value

    @property
    def message_type(self) -> str:
        """
        Override the message_type property to always return "ActionMessage"
        for ActionMessage and its subclasses.
        """
        return "ActionMessage"

    @property
    def additional_metadata(self) -> str:
        return self._additional_metadata

    @property
    def memory(self):
        return self._memory

    @memory.setter
    def memory(self, x: str):
        """This should only be set by the MemoryResource."""
        self._memory = x

    def action_dict(self) -> dict:
        action_dict = {
            "resource_id": self.resource_id,
            "message": self.message,
        }
        if self.additional_metadata:
            action_dict["additional_metadata"] = self.additional_metadata
        return action_dict

    def to_broadcast_dict(self) -> dict:
        base_dict = super().to_broadcast_dict()
        action_dict = self.action_dict()
        action_dict.update(base_dict)
        return action_dict

    def to_log_dict(self) -> dict:
        base_dict = super().to_log_dict()
        action_dict = self.action_dict()
        action_dict.update(base_dict)
        return action_dict

    @classmethod
    def from_dict(cls, data: dict) -> "ActionMessage":
        """Reconstruct an action message from its dictionary representation"""

        if cls is ActionMessage and "command" in data:
            from messages.action_messages.command_message import CommandMessage

            return CommandMessage.from_dict(data)

        resource_id = data.get("resource_id")
        message = data.get("message", "")
        additional_metadata = data.get("additional_metadata", {})

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

        return action_message
