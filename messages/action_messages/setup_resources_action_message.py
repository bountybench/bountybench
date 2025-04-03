from typing import Any, Dict, List, Optional

from messages.action_messages.action_message import ActionMessage
from messages.action_messages.script_action_message import ScriptActionMessage


class SetupResourcesMessage(ScriptActionMessage):
    """
    Action message for setup resources to capture output from start operations.
    """
    
    def __init__(
        self,
        resource_id: str,
        command: Optional[str] = "",
        message: Optional[str] = "",
        exit_code: Optional[int] = None,
        container_names: Optional[List[str]] = None,
        setup_script_name: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        prev: Optional[ActionMessage] = None,
    ) -> None:
        _additional_metadata = {
            "container_names": container_names or [],
            "setup_script_name": setup_script_name,
        }
        
        # Merge with any additional metadata provided
        if additional_metadata:
            _additional_metadata.update(additional_metadata)
            
        super().__init__(
            resource_id=resource_id,
            command=command,
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
    def setup_script_name(self) -> Optional[str]:
        """Name of the setup script that was executed."""
        return self.additional_metadata.get("setup_script_name")
    
    def set_container_names(self, container_names: List[str]) -> None:
        """Update the list of container names."""
        self.additional_metadata["container_names"] = container_names
    
    def set_setup_script_name(self, script_name: str) -> None:
        """Set the name of the setup script."""
        self.additional_metadata["setup_script_name"] = script_name
    
    def add_container(self, container_name: str) -> None:
        """Add a container to the list of containers."""
        if container_name not in self.container_names:
            self.additional_metadata["container_names"].append(container_name)
    
    def is_successful(self) -> bool:
        """
        Determine if the setup operation was successful.
        Success is determined by exit_code being 0.
        """
        if self.exit_code is None:
            return False
            
        return self.exit_code == 0