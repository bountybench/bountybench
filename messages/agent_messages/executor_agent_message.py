from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message

class ExecutorAgentMessage(AgentMessage):
    @property
    def message(self) -> str:
        self._message = ""
        current_action_messages = self.current_actions_list
        for action_message in current_action_messages:
            if action_message:
                self._message += action_message.message

        return self._message
