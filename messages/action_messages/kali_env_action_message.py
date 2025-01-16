from messages.action_messages.action_message import ActionMessage

class KaliEnvActionMessage(ActionMessage):
    def __init__(self, message: str, resource_id: str, observation: str, prev: ActionMessage = None) -> None:
        super().__init__(message, prev, resource_id)
        self._observation = observation

    @property
    def observation(self) -> bool:
        return self._observation
    
    def to_dict(self) -> dict:
        base_dict = super().to_dict()        
        base_dict.update({
            "observation": self.observation
        })
        return base_dict