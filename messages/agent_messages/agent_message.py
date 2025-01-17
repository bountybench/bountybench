from typing import List
from messages.action_messages.action_message import ActionMessage
from messages.message import Message

class AgentMessage(Message):
    _action_messages: List[ActionMessage] = []
    def __init__(self, agent_id: str, prev: 'AgentMessage' = None) -> None:
        super().__init__(prev)
        self._agent_id = agent_id

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def action_messages(self) -> List[ActionMessage]:
        return self._action_messages
   
    def add_action_message(self, action_message: ActionMessage):
        self._action_messages.append(action_message)

    def to_dict(self) -> dict:
        base_dict = super().to_dict()        
        base_dict.update({
            "agent_id": self.agent_id,
            "action_messages": [action_message.to_dict() for action_message in self.action_messages]
        })
        return base_dict