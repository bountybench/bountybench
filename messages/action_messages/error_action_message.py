from typing import Any, Dict, List, Optional

from messages.action_messages.action_message import ActionMessage


class ErrorActionMessage(ActionMessage):
    def __init__(
        self,
        resource_id: str,
        message: Optional[str] = "",
        error_type: Optional[str] = None,
        error_history: Optional[List[str]] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        prev: Optional[ActionMessage] = None,
    ) -> None:

        additional_metadata = additional_metadata or {}
        additional_metadata["error_type"] = error_type
        additional_metadata["error_history"] = error_history

        super().__init__(resource_id, message, additional_metadata, prev)

    @property
    def error_type(self) -> str:
        return self.additional_metadata["error_type"]

    @property
    def error_history(self) -> List[str]:
        return self.additional_metadata["error_history"]
