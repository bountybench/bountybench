from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message

class ExecutorAgentMessage(AgentMessage):
    @property
    def message(self) -> str:
        self._message = ""
        #TODO: add version history
        for action_message in self.action_messages:
            self._message += action_message.message

        return self._message
