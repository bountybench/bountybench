from typing import Any, Dict, List, Optional

from messages.action_messages.action_message import ActionMessage


class SetupActionMessage(ActionMessage):
    """
    Action message for setup resources to capture output from start operations.
    """
    
    def __init__(
        self,
        resource_id: str,
        message: Optional[str] = "",
        exit_code: Optional[int] = None,
        container_names: Optional[List[str]] = None,
        script_output: Optional[str] = None,
        script_error: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        prev: Optional[ActionMessage] = None,
    ) -> None:
        _additional_metadata = {
            "container_names": container_names or [],
            "script_output": script_output or "",
            "script_error": script_error or "",
        }
        
        # Merge with any additional metadata provided
        if additional_metadata:
            _additional_metadata.update(additional_metadata)
            
        super().__init__(
            resource_id=resource_id,
            message=message,
            exit_code=exit_code,
            additional_metadata=_additional_metadata,
            prev=prev,
        )
    
    @property
    def container_names(self) -> List[str]:
        """List of container names managed by this setup operation."""
        return self.additional_metadata.get("container_names", [])
    
    @property
    def script_output(self) -> str:
        """Standard output from the setup script execution."""
        return self.additional_metadata.get("script_output", "")
    
    @property
    def script_error(self) -> str:
        """Standard error from the setup script execution."""
        return self.additional_metadata.get("script_error", "")
    
    def set_container_names(self, container_names: List[str]) -> None:
        """Update the list of container names."""
        self.additional_metadata["container_names"] = container_names
    
    def set_script_output(self, output: str) -> None:
        """Set the script standard output."""
        self.additional_metadata["script_output"] = output
    
    def set_script_error(self, error: str) -> None:
        """Set the script standard error."""
        self.additional_metadata["script_error"] = error
    
    def add_container(self, container_name: str) -> None:
        """Add a container to the list of containers."""
        if container_name not in self.container_names:
            self.additional_metadata["container_names"].append(container_name)
    
    def is_successful(self) -> bool:
        """
        Determine if the setup operation was successful.
        For a start operation, success means exit_code is 0 and at least one container is present.
        For a stop operation, success is determined by exit_code alone.
        """
        if self.exit_code is None:
            return False
            
        return self.exit_code == 0