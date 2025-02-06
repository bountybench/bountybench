from typing import Optional
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message

class ExecutorAgentMessage(AgentMessage):
    def __init__(self, agent_id: str, message: Optional[str] = "", prev: 'AgentMessage' = None):
        """
        Initializes ExecutorAgentMessage with agent_id, message, and optional prev message.
        """
        super().__init__(agent_id=agent_id, message=message, prev=prev)  # Pass parameters to AgentMessage
        self._message = message  # Initialize the private attribute

    @property
    def message(self) -> str:
        """
        Getter for message property that aggregates messages from current actions.
        """
        if self._message:  # If manually set, return it
            return self._message
        current_action_messages = self.current_actions_list
        for action_message in current_action_messages:
            if action_message and action_message.message:
                self._message += action_message.message

        return self._message

    @message.setter
    def message(self, value: str):
        """
        Setter for message property.
        """
        self._message = value  # Allow external setting
