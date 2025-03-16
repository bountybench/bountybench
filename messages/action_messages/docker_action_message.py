from typing import Optional

from messages.action_messages.action_message import ActionMessage


class DockerActionMessage(ActionMessage):
    def __init__(
        self,
        resource_id: str,
        message: str,
        exit_code: Optional[int] = None,
        prev: Optional[ActionMessage] = None,
    ) -> None:
        additional_metadata = {
            "exit_code": exit_code,
        }

        super().__init__(resource_id, message, additional_metadata, prev)

    @property
    def exit_code(self) -> Optional[int]:
        return self.additional_metadata.get("exit_code")
