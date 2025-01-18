from messages.message import Message
from typing import Dict, Any, Optional

class ActionMessage(Message):
    def __init__(self, resource_id: str, message: str, additional_metadata: Optional[Dict[str, Any]] = {}, prev: 'ActionMessage' = None) -> None:
        self._resource_id = resource_id
        self._message = message
        self._additional_metadata = additional_metadata
        super().__init__(prev)

    @property
    def resource_id(self) -> str:
        return self._resource_id

    @property
    def message(self) -> str:
        return self._message
    
    @property
    def additional_metadata(self) -> str:
        return self._additional_metadata

    def to_dict(self) -> dict:
        resource_dict = {
            "resource_id": self.resource_id,
            "message": self.message
        }
        base_dict = super().to_dict()
        resource_dict.update(base_dict)
        return resource_dict