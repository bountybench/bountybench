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
        """
        Start a workflow and return its ID, model, and status info.

        Returns:
            Dict[str, Any]: A dictionary containing workflow ID, model name, and status {initializing}.
        """
        pass
    
    @abstractmethod
    async def stop_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Stop a running workflow.

        Returns:
            Dict[str, Any]: A dictionary containing workflow ID and status {stopped}.        
        """
        pass
    
    @abstractmethod
    async def restart_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Restart a workflow.

        Returns:
            Dict[str, Any]: A dictionary containing workflow ID and status {restarting}.
        """
        pass
    
    @abstractmethod
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the current status of a workflow.

        Returns:
            Dict[str, Any]: A dictionary containing workflow ID and its current status.
        """
        pass

    @abstractmethod
    async def get_workflow_appheader(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the workflow metadata for AppHeader.

        Returns:
            Dict[str, Any]: A dictionary containing workflow ID and its model,
            interactive mode, and use mock model status.
        """
    
    @abstractmethod
    async def list_active_workflows(self) -> List[Dict[str, Any]]:
        """
        List all active workflows.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing details of all active workflows:
                - id: The workflow ID
                - status: Current workflow status
                - name: Workflow class name
                - task: The workflow task
                - timestamp: Timestamp of the last workflow message
        """
        pass
    
    @abstractmethod
    async def run_message(self, workflow_id: str, message_data: MessageData) -> Dict[str, Any]:
        """
        Run a specific message in the workflow.
        
        Returns:
            Dict[str, Any]: A dictionary containing
                - status: The operation status (updated).
                - result.id: The 'id' attribute of an `Message` object.
        """
        pass
    
    @abstractmethod
    async def edit_message(self, workflow_id: str, message_data: MessageInputData) -> Dict[str, Any]:
        """
        Edit and run a message in the workflow.

        Returns:
            Dict[str, Any]: A dictionary containing
                - status: The operation status (updated).
                - result.id: The 'id' attribute of an `Message` object.
        """
        pass
    
    @abstractmethod
    async def update_interactive_mode(self, workflow_id: str, data: UpdateInteractiveModeInput) -> Dict[str, Any]:
        """
        Update the interactive mode of a workflow.

        Returns:
            Dict[str, Any]: A dictionary containing status (success) and new_interactive_mode (bool).
        """
        pass
    
    @abstractmethod
    async def get_last_message(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the last message from a workflow.
        
        Returns:
            Dict[str, Any]: A dictionary containing message_type (last_message) and content (str).
        """
        pass
    
    @abstractmethod
    async def handle_websocket_connection(self, workflow_id: str, websocket):
        """
        Handle a websocket connection for a workflow.        
        """
        pass
    
    @abstractmethod
    async def change_model(self, workflow_id: str, new_model_name: str) -> Dict[str, Any]:
        """
        Change the model for a workflow.
        
        Returns:
            Dict[str, Any]: A dictionary containing
                - status: The operation status (updated).
                - result.id: The 'id' attribute of an `Message` object.
        """
        pass
    
    @abstractmethod
    async def toggle_version(self, workflow_id: str, message_id: str, direction: str) -> Dict[str, Any]:
        """
        Toggle between versions of a message.
        
        Returns:
            Dict[str, Any]: A dictionary containing
                - status: The operation status (updated).
                - result.id: The 'id' attribute of an `Message` object.
        """
        pass
    
    @abstractmethod
    async def get_workflow_resources(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the resources associated with a workflow.
        
        Returns:
            Dict[str, Any]: A dictionary containing a list of resource info dictionaries.
        """
        pass
    
    @abstractmethod
    async def update_mock_model_mode(self, workflow_id: str, use_mock_model: bool) -> Dict[str, Any]:
        """
        Update the mock model mode for a workflow.
        
        Returns:
            Dict[str, Any]: A dictionary containing status (success) and use_mock_model (bool).
        """
        pass

    @abstractmethod
    async def save_config(self, filename: str, config_content: str) -> Dict[str, Any]:
        """
        Save configuration to appropriate local or managed storage.
        
        Returns:
            Dict[str, Any]: A dictionary containing message (success message content).
        """
        pass