from typing import Dict, Any, Optional
from messages.action_messages.action_message import ActionMessage

class BrowserMessage(ActionMessage):
    def __init__(
        self,
        resource_id: str,
        message: str,
        additional_metadata: Optional[Dict[str, Any]] = None,
        prev: "ActionMessage" = None,
    ) -> None:
        """
        BrowserMessage represents a structured message containing browser automation commands.

        :param resource_id: The ID of the resource handling this message.
        :param message: A description of the browser action.
        :param additional_metadata: Dictionary containing URL, actions, and input details.
        :param prev: Optional reference to a previous message in the workflow.
        """
        super().__init__(resource_id, message, additional_metadata, prev)

    @property
    def url(self) -> str:
        """Returns the URL from additional metadata."""
        return self.additional_metadata.get("url", "")

    @property
    def actions(self) -> list:
        """Returns the list of actions to perform on the page."""
        return self.additional_metadata.get("actions", [])

    @property
    def inputs(self) -> dict:
        """Returns the dictionary of input data for form interactions."""
        return self.additional_metadata.get("inputs", {})

    def to_dict(self) -> dict:
        """Converts the BrowserMessage into a dictionary format."""
        action_dict = super().to_dict()
        action_dict.update({
            "url": self.url,
            "actions": self.actions,
            "inputs": self.inputs
        })
        return action_dict
