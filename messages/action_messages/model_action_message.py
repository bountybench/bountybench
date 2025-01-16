from messages.action_messages.action_message import ActionMessage

class ModelActionMessage(ActionMessage):
    def __init__(self, message: str, resource_id: str, response: str, prev: ActionMessage = None) -> None:
        super().__init__(message, prev, resource_id)
        self._response = response

    @property
    def response(self) -> bool:
        return self._response
    
    def to_dict(self) -> dict:
        base_dict = super().to_dict()        
        base_dict.update({
            "response": self.response
        })
        return base_dict