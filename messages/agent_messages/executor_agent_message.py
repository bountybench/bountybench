from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message

class ExecutorAgentMessage(AgentMessage):
    def __init__(self, agent_id: str, response: str, observation: str, prev: 'Message' = None) -> None:
        super().__init__(agent_id, prev)
        self._response = response
        self._observation = observation

    @property
    def response(self) -> str:
        return self._response

    @property
    def observation(self) -> str:
        return self._observation

    def to_dict(self) -> dict:
        base_dict = super().to_dict()
        base_dict.update({
            "response": self.response,
            "observation": self.observation
        })
        return base_dict