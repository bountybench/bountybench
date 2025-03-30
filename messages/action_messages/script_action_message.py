from typing import Any, Dict, Optional

from messages.action_messages.action_message import ActionMessage


class ScriptActionMessage(ActionMessage):
    def __init__(
        self,
        resource_id: str,
        command: str,
        message: Optional[str] = "",
        exit_code: Optional[int] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        prev: Optional[ActionMessage] = None,
    ) -> None:

        additional_metadata = additional_metadata or {}
        additional_metadata["exit_code"] = exit_code
        additional_metadata["command"] = command

        super().__init__(resource_id, message, additional_metadata, prev)

    @property
    def command(self) -> str:
        return self.additional_metadata["command"]

    @property
    def exit_code(self) -> Optional[int]:
        return self.additional_metadata.get("exit_code")

    def set_exit_code(self, exit_code) -> None:
        self.additional_metadata["exit_code"] = exit_code
