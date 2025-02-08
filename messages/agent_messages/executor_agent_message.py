from typing import Optional
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message

class ExecutorAgentMessage(AgentMessage):
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
