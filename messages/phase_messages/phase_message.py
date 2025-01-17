from typing import List, Optional
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message

class PhaseMessage(Message):
    def __init__(self, prev: 'PhaseMessage' = None, agent_messages: Optional[List[AgentMessage]] = []) -> None:
        super().__init__(prev)
        self._success = False
        self._complete = False
        self._agent_messages = agent_messages
        self._phase_summary = None
    
    @property
    def success(self) -> bool:
        return self._success
    
    @property
    def complete(self) -> bool:
        return self._complete
    
    @property
    def agent_messages(self) -> List[AgentMessage]:
        return self._agent_messages
    
    @property
    def phase_summary(self) -> str:
        return self._phase_summary

    def set_success(self):
        self._success = True

    def set_complete(self):
        self._complete = True

    def add_agent_message(self, agent_message: Message):
        self._agent_messages.append(agent_message)

    def to_dict(self) -> dict:
        base_dict = super().to_dict()        
        base_dict.update({
            "success": self.success,
            "complete": self.complete,
            "agent_messages": [agent_message.to_dict() for agent_message in self.agent_messages],
            "phase_summary": self.phase_summary
        })
        return base_dict