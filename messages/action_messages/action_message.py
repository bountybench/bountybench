from typing import Any, Dict, Optional

from messages.message import Message


class ActionMessage(Message):
    def __init__(
        self,
        resource_id: str,
        message: str,
        additional_metadata: Optional[Dict[str, Any]] = None,
        prev: "ActionMessage" = None,
    ) -> None:
        self._resource_id = resource_id
        self._message = message
        self._additional_metadata = (
            additional_metadata[0] if isinstance(additional_metadata, tuple) and additional_metadata
            else additional_metadata if isinstance(additional_metadata, dict)
            else {}
        )
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
    def additional_metadata(self) -> Dict[str, Any]:
        return self._additional_metadata

    def add_to_additional_metadata(self, key: str, value: Any) -> None:
        self._additional_metadata[key] = value

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
