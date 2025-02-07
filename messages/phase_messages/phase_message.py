from typing import List, Optional

from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message


class PhaseMessage(Message):
    def __init__(
        self, phase_id: str, prev: "PhaseMessage" = None, attrs: dict = None
    ) -> None:
        self._phase_id = phase_id
        self._success = False
        self._complete = False
        self._agent_messages = []
        self._phase_summary = None
        super().__init__(prev=prev, attrs=attrs)

    @property
    def phase_id(self) -> str:
        return self._phase_id

    @property
    def workflow_id(self) -> str:
        if self.parent:
            return self.parent.workflow_id
        return None

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
    
    @property
    def current_agent_list(self) -> List[AgentMessage]:
        current_agents = []
        if len(self.agent_messages) > 0:
            current_message = self.agent_messages[0]
            current_message = self.get_latest_version(current_message)

            current_agents.append(current_message)
            while (
                current_message.next
                and current_message.next.prev
                and current_message.next.prev.id == current_message.id
            ):
                current_message = current_message.next
                current_message = self.get_latest_version(current_message)
                current_agents.append(current_message)

        return current_agents

    def set_success(self):
        self._success = True

    def set_complete(self):
        self._complete = True

    def set_summary(self, summary: str):
        self._phase_summary = summary

    def add_agent_message(self, agent_message: AgentMessage):
        self._agent_messages.append(agent_message)
        agent_message.set_parent(self)
        from messages.message_utils import log_message

        log_message(self)

    def to_dict(self) -> dict:
        phase_dict = {
            "phase_id": self.phase_id,
            "phase_summary": self.phase_summary,
            "agent_messages": (
                [
                    agent_message.to_dict()
                    for agent_message in self.agent_messages
                    if agent_message is not None
                ]
                if self.agent_messages
                else None
            ),
            "current_children": [
                agent_message.to_dict() for agent_message in self.current_agent_list
            ],
        }
        base_dict = super().to_dict()
        phase_dict.update(base_dict)
        return phase_dict

    @classmethod
    def from_dict(cls, data: dict) -> "PhaseMessage":
        phase_id = data.get('phase_id')
        phase_summary = data.get('phase_summary')
        attrs = {
            key: data[key] 
            for key in data 
            if key not in ['message_type', 'phase_id', 'phase_summary', 'agent_messages']
        }
        phase_message = cls(
            phase_id=phase_id, 
            attrs=attrs
        )
        
        phase_message.set_summary(phase_summary)

        for agent_data in data.get("agent_messages", []):
            from messages.message_utils import message_from_dict
            agent_message = message_from_dict(agent_data)
            phase_message.add_agent_message(agent_message)

        return phase_message