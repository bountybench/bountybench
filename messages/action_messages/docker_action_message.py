from messages.action_messages.action_message import ActionMessage
from typing import Dict, Any, Optional

class DockerActionMessage(ActionMessage):
    def __init__(
        self,
        resource_id: str,
        message: str,
        docker_image: str,
        command: str,
        network: Optional[str] = None,
        volumes: Optional[Dict[str, Any]] = None,
        output: Optional[str] = None,
        exit_code: Optional[int] = None,
        success: Optional[bool] = None,
        prev: Optional[ActionMessage] = None,
    ) -> None:
        additional_metadata = {
            "docker_image": docker_image,
            "command": command,
            "network": network,
            "volumes": volumes or {},
            "output": output,
            "exit_code": exit_code,
            "success": success,
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

    @property
    def output(self) -> Optional[str]:
        return self.additional_metadata.get("output")

    @property
    def exit_code(self) -> Optional[int]:
        return self.additional_metadata.get("exit_code")

    @property
    def success(self) -> Optional[bool]:
        return self.additional_metadata.get("success")