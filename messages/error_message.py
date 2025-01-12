from messages.message import Message
from typing import Optional

class ErrorMessage(Message):
    def __init__(self, answer: str, error: bool, metadata: Optional[dict] = None) -> None:
        self._message = answer
        self._answer = answer
        self._error = error
        self._metadata = metadata
 
    @property
    def message(self) -> str:
        return self._message
    
    @property
    def answer(self) -> str:
        return self._answer

    @property
    def error(self) -> bool:
        return self._error
    
    @property
    def metadata(self) -> dict:
        return self._metadata
    
    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "answer": self.answer,
            "error": self.error,
            "metadata": self.metadata
        }