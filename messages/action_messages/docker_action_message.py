from typing import Any, Dict, Optional

from messages.action_messages.action_message import ActionMessage
from messages.action_messages.script_action_message import ScriptActionMessage


class DockerActionMessage(ScriptActionMessage):
    def __init__(
        self,
        resource_id: str,
        docker_image: str,
        command: str,
        message: Optional[str] = "",
        network: Optional[str] = None,
        volumes: Optional[Dict[str, Any]] = None,
        exit_code: Optional[int] = None,
        prev: Optional[ActionMessage] = None,
    ) -> None:
        additional_metadata = {
            "docker_image": docker_image,
            "network": network,
            "volumes": volumes or {},
        }

        super().__init__(
            resource_id,
            command=command,
            message=message,
            exit_code=exit_code,
            additional_metadata=additional_metadata,
            prev=prev,
        )

    @property
    def docker_image(self) -> str:
        return self.additional_metadata["docker_image"]

    @property
    def network(self) -> Optional[str]:
        return self.additional_metadata.get("network")

    @property
    def volumes(self) -> Dict[str, Any]:
        return self.additional_metadata.get("volumes", {})
