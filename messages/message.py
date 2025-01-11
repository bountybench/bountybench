from messages.message_interface import MessageInterface

class Message(MessageInterface): 
    def __init__(self, message: str) -> None:
        self._message = message

    @property
    def message(self) -> str:
        return self._message
    
    def to_dict(self) -> dict:
        return {
            "message": self.message
        }