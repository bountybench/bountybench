from typing import List, Optional
from messages.action_messages.action_message import ActionMessage
from messages.message import Message



class AgentMessage(Message):
    
    def __init__(self, agent_id: str, message: Optional[str] = "", prev: 'AgentMessage' = None, input_str: Optional[str] = None) -> None:
        self._message = message
        self._agent_id = agent_id
        self._action_messages = []
        self._input_str = input_str

        super().__init__(prev)


    @property
    def message(self) -> str:
        return self._message

    
    @property
    def input_str(self) -> Optional[str]:
        return self._input_str
    
    @property
    def message_type(self) -> str:
        """
        Override the message_type property to always return "AgentMessage"
        for AgentMessage and its subclasses.
        """
        return "AgentMessage"
    
    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def action_messages(self) -> List[ActionMessage]:
        return self._action_messages
   
    def add_action_message(self, action_message: ActionMessage):
        self._action_messages.append(action_message)
        action_message.set_parent(self)
        from messages.message_utils import broadcast_update
        broadcast_update(self.to_dict())

    def agent_dict(self) -> dict:
        agent_dict = {
            "agent_id": self.agent_id,
            "action_messages": [action_message.to_dict() for action_message in self.action_messages if action_message is not None] if self.action_messages else None,
            "message": self.message
        }
        if self.input_str is not None:
            agent_dict["input"] = self.input_str

        return agent_dict
    
    def to_dict(self) -> dict:
        agent_dict = self.agent_dict()
        base_dict = super().to_dict() 
        agent_dict.update(base_dict)
        return agent_dict