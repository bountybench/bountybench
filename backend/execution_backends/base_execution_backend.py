from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, List

from backend.schema import (
    StartWorkflowInput, 
    MessageData, 
    MessageInputData,
    UpdateInteractiveModeInput
)

class ExecutionBackend(ABC):
    """Abstract interface for workflow execution backends."""
    
    def __init__(self, workflow_factory: Dict[str, Callable]):
        self.workflow_factory = workflow_factory
    
    @abstractmethod
    async def start_workflow(self, workflow_data: StartWorkflowInput) -> Dict[str, Any]:
        """Start a workflow and return its ID, model, and status info."""
        pass
    
    @abstractmethod
    async def stop_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Stop a running workflow."""
        pass
    
    @abstractmethod
    async def restart_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Restart a workflow."""
        pass
    
    @abstractmethod
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get the current status of a workflow."""
        pass
    
    @abstractmethod
    async def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows."""
        pass
    
    @abstractmethod
    async def run_message(self, workflow_id: str, message_data: MessageData) -> Dict[str, Any]:
        """Run a specific message in the workflow."""
        pass
    
    @abstractmethod
    async def edit_message(self, workflow_id: str, message_data: MessageInputData) -> Dict[str, Any]:
        """Edit and run a message in the workflow."""
        pass
    
    @abstractmethod
    async def update_interactive_mode(self, workflow_id: str, data: UpdateInteractiveModeInput) -> Dict[str, Any]:
        """Update the interactive mode of a workflow."""
        pass
    
    @abstractmethod
    async def get_last_message(self, workflow_id: str) -> Dict[str, Any]:
        """Get the last message from a workflow."""
        pass
    
    @abstractmethod
    async def handle_websocket_connection(self, workflow_id: str, websocket):
        """Handle a websocket connection for a workflow."""
        pass
    
    @abstractmethod
    async def change_model(self, workflow_id: str, new_model_name: str) -> Dict[str, Any]:
        """Change the model for a workflow."""
        pass
    
    @abstractmethod
    async def toggle_version(self, workflow_id: str, message_id: str, direction: str) -> Dict[str, Any]:
        """Toggle between versions of a message."""
        pass
    
    @abstractmethod
    async def get_workflow_resources(self, workflow_id: str) -> Dict[str, Any]:
        """Get the resources associated with a workflow."""
        pass
    
    @abstractmethod
    async def update_mock_model_mode(self, workflow_id: str, use_mock_model: bool) -> Dict[str, Any]:
        """Update the mock model mode for a workflow."""
        pass

    @abstractmethod
    async def save_config(self, filename: str, config_content: str) -> Dict[str, Any]:
        """Save configuration to appropriate storage."""
        pass