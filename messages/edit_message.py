from messages.message_interface import MessageInterface

class EditMessage(MessageInterface): 
    def __init__(self, message: str) -> None:
        self._message = message

    def add(self, text: str):
        self._message += text

    def edit(self, text: str):
        self._message = text

    @property
    def message(self) -> str:
        return self._message
    
    def to_dict(self) -> dict:
        return {
            "message": self.message
        }