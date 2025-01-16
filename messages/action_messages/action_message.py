from messages.action_messages.action_message_interface import ActionMessageInterface
from messages.message import Message

class ActionMessage(Message, ActionMessageInterface):
    def __init__(self, message: str, resource_id: str, prev: 'ActionMessage' = None) -> None:
        super().__init__(message, prev)
        self._resource_id = resource_id

    @property
    def resource_id(self) -> str:
        return self._resource_id

    def to_dict(self) -> dict:
        base_dict = super().to_dict()        
        base_dict.update({
            "resource_id": self.resource_id
        })
        return base_dict