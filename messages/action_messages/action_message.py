from typing import Any, Dict, Optional

from messages.message import Message


class ActionMessage(Message):
    def __init__(
        self,
        resource_id: str,
        message: str,
        additional_metadata: Optional[Dict[str, Any]] = {},
        prev: "ActionMessage" = None,
        attrs: dict = None,
    ) -> None:
        self._resource_id = resource_id
        self._message = message
        self._additional_metadata = additional_metadata

        super().__init__(prev=prev, attrs=attrs)

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

    def action_dict(self) -> dict:
        action_dict = {
            "resource_id": self.resource_id,
            "message": self.message,
        }
        if self.additional_metadata:
            action_dict["additional_metadata"] = self.additional_metadata

        return action_dict

    def to_dict(self) -> dict:
        action_dict = self.action_dict()
        base_dict = super().to_dict()
        action_dict.update(base_dict)
        return action_dict

    @classmethod
    def from_dict(cls, data: dict) -> "ActionMessage":
        action_message = cls(
            resource_id=data["resource_id"],
            message=data["message"],
            additional_metadata=data.get("additional_metadata"),
            attrs={
                "prev": data.get("prev"),
                "next": data.get("next"),
                "version_prev": data.get("version_prev"),
                "version_next": data.get("version_next"),
                "parent": data.get("parent"),
                "current_id": data.get("current_id"),
                "timestamp": data.get("timestamp"),
            },
        )

        return action_message
