from typing import Any, Dict, List
from phase_messages.phase_message_interface import PhaseMessageInterface
from messages.message import Message

class PhaseMessage(PhaseMessageInterface):
    def __init__(self, agent_messages: List[Message]) -> None:
        self._success = False
        self._complete = False
        self._agent_messages = agent_messages
    
    @property
    def success(self) -> bool:
        return self._success
    
    @property
    def complete(self) -> bool:
        return self._complete
    
    @property
    def agent_messages(self) -> List[Message]:
        return self._agent_messages

    def set_success(self):
        self._success = True

    def set_complete(self):
        self._complete = True

    def add_agent_message(self, agent_message: Message):
        self._agent_messages.append(agent_message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "complete": self.complete,
            "agent_messages": [agent_message.to_dict() for agent_message in self.agent_messages]
        }
