from messages.agent_messages.agent_message import AgentMessage


class ExecutorAgentMessage(AgentMessage):
    @property
    def message(self) -> str:
        """
        Getter for message property that aggregates messages from current actions.
        """
        current_action_messages = self.current_children
        if current_action_messages:
            message = ""
            for action_message in current_action_messages:
                if action_message and action_message.message:
                    message += action_message.message
            return message
        elif self._message:
            # Else if manually set (e.g. an agent error message), return it
            return self._message

        return ""
