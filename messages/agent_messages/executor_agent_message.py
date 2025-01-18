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
        agent_dict = self.agent_dict()
        agent_dict.update({
            "response": self.response,
            "observation": self.observation
        })
        base_dict = super(AgentMessage, self).to_dict() 
        agent_dict.update(base_dict)
        return agent_dict