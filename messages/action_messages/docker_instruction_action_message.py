from typing import Any, Dict, Optional

from messages.action_messages.action_message import ActionMessage


class DockerInstructionActionMessage(ActionMessage):
    def __init__(
        self,
        resource_id: str,
        message: str,
        docker_image: str,
        command: str,
        network: Optional[str] = None,
        volumes: Optional[Dict[str, Any]] = None,
        prev: Optional[ActionMessage] = None,
    ) -> None:
        additional_metadata = {
            "docker_image": docker_image,
            "command": command,
            "network": network,
            "volumes": volumes or {},
        }

        super().__init__(resource_id, message, additional_metadata, prev)

    @property
    def docker_image(self) -> str:
        return self.additional_metadata["docker_image"]

    @property
    def command(self) -> str:
        return self.additional_metadata["command"]

    @property
    def network(self) -> Optional[str]:
        return self.additional_metadata.get("network")

    @property
    def volumes(self) -> Dict[str, Any]:
        return self.additional_metadata.get("volumes", {})
