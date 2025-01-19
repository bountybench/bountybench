from typing import List, Optional
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message

class PhaseMessage(Message):
    def __init__(self, prev: 'PhaseMessage' = None, agent_messages: Optional[List[AgentMessage]] = []) -> None:
        self._success = False
        self._complete = False
        self._summary = "incomplete"
        self._agent_messages = agent_messages
        self._phase_summary = None
        super().__init__(prev)

    
    @property
    def success(self) -> bool:
        return self._success
    
    @property
    def complete(self) -> bool:
        return self._complete
    
    @property
    def summary(self) -> bool:
        return self._summary
    
    @property
    def agent_messages(self) -> List[AgentMessage]:
        return self._agent_messages
    
    @property
    def phase_summary(self) -> str:
        return self.summary
  
    def set_success(self):
        self._success = True

    def set_complete(self):
        self._complete = True

    def set_summary(self, summary: str):
        self._summary = summary

    def add_agent_message(self, agent_message: AgentMessage):
        self._agent_messages.append(agent_message)

    def to_dict(self) -> dict:
        phase_dict = {
            "phase_summary": self.summary,
            "agent_messages": [agent_message.to_dict() for agent_message in self.agent_messages],
            "phase_summary": self.phase_summary
        }
        base_dict = super().to_dict()
        phase_dict.update(base_dict)
        return phase_dict
