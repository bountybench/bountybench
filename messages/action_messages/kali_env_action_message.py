from messages.action_messages.action_message import ActionMessage

class KaliEnvActionMessage(ActionMessage):
    def __init__(self, message: str, resource_id: str, prev: ActionMessage = None) -> None:
        super().__init__(message, prev, resource_id)

    def to_dict(self) -> dict:
        base_dict = super().to_dict()        
        base_dict.update({
            "observation": self.observation
        })
        return base_dict