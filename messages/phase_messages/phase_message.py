from typing import List, Optional
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message

class PhaseMessage(Message):
    def __init__(self, phase_id: str, prev: 'PhaseMessage' = None, agent_messages: Optional[List[AgentMessage]] = []) -> None:
        self._phase_id = phase_id
        self._success = False
        self._complete = False
        self._summary = "incomplete"
        self._agent_messages = agent_messages
        self._phase_summary = None
        super().__init__(prev)
        from messages.message_utils import update_message
        update_message(self)

    @property
    def phase_id(self) -> str:
        return self._phase_id
    
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
  
    @property 
    def current_agent_list(self) -> List[AgentMessage]:
        current_agents = []
        if len(self.agent_messages) > 0:
            current_message = self.agent_messages[0]
            current_message = self.get_latest_version(current_message)

            current_agents.append(current_message)
            while current_message.next:
                current_message = current_message.next
                current_message = self.get_latest_version(current_message)
                current_agents.append(current_message)
            
        return current_agents

    def set_success(self):
        self._success = True

    def set_complete(self):
        self._complete = True

    def set_summary(self, summary: str):
        self._summary = summary

    def add_agent_message(self, agent_message: AgentMessage):
        self._agent_messages.append(agent_message)
        agent_message.set_parent(self)
        from messages.message_utils import broadcast_update
        phase_dict = self.to_dict()
        phase_dict["current_children"] = [agent_message.to_dict() for agent_message in self.current_agent_list]
        broadcast_update(phase_dict)


    def to_dict(self) -> dict:
        phase_dict = {
            "phase_id": self.phase_id,
            "phase_summary": self.summary,
            "agent_messages": [agent_message.to_dict() for agent_message in self.agent_messages if agent_message is not None] if self.agent_messages else None,
            "phase_summary": self.phase_summary
        }
        base_dict = super().to_dict()
        phase_dict.update(base_dict)
        return phase_dict
