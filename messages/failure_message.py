from messages.message_interface import MessageInterface

class FailureMessage(MessageInterface):
    def __init__(self, message: str) -> None:
        self._failure_reason = message
        self._message = "Failure Message"
 
    @property
    def message(self) -> str:
        return self._message
    
    @property
    def failure_reason(self) -> str:
        return self._failure_reason
    
    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "failure_reason": self.failure_reason
        }