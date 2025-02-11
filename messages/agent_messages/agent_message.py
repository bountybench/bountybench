from typing import List, Optional
from messages.action_messages.action_message import ActionMessage
from messages.message import Message



class AgentMessage(Message):
    
    def __init__(self, agent_id: str, message: Optional[str] = "", prev: 'AgentMessage' = None) -> None:
        self._message = message
        self._agent_id = agent_id
        self._action_messages = []
        self._memory = None 

        super().__init__(prev)


    @property
    def message(self) -> str:
        return self._message
    
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
    def workflow_id(self) -> str:
        if self.parent:
            return self.parent.workflow_id
        return None
    
    @property
    def action_messages(self) -> List[ActionMessage]:
        return self._action_messages

    @property 
    def current_children(self) -> List[ActionMessage]:
        current_actions = []
        if len(self.action_messages) > 0:
            current_message = self.action_messages[0]
            current_message = current_message.get_latest_version()

            current_actions.append(current_message)
            while current_message.next and current_message.next.prev and current_message.next.prev.id == current_message.id:
                current_message = current_message.next
                current_message = current_message.get_latest_version()
                current_actions.append(current_message)
            
        return current_actions
    
    @property
    def memory(self): 
        return self._memory

    @memory.setter
    def memory(self, x: str): 
        """This should only be set by the MemoryResource."""
        self._memory = x
    
    def add_action_message(self, action_message: ActionMessage):
        self._action_messages.append(action_message)
        action_message.set_parent(self)
        from messages.message_utils import log_message
        log_message(action_message)
        log_message(self)

    def agent_dict(self) -> dict:
        agent_dict = {
            "agent_id": self.agent_id,
            "action_messages": [action_message.to_dict() for action_message in self.action_messages if action_message is not None] if self.action_messages else None,
            "message": self.message
        }
        agent_dict["current_children"] = [action_message.to_dict() for action_message in self.current_children]
        
        return agent_dict
    
    def to_dict(self) -> dict:
        agent_dict = self.agent_dict()
        base_dict = super().to_dict() 
        agent_dict.update(base_dict)
        return agent_dict