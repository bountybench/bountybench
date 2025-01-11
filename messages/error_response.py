from responses.response import Response
from typing import Optional

class ErrorResponse(Response):
    def __init__(self, answer: str, error: bool, metadata: Optional[dict] = None) -> None:
        self._response = answer
        self._answer = answer
        self._error = error
        self._metadata = metadata
 
    @property
    def response(self) -> str:
        return self._response
    
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
            "response": self.response,
            "answer": self.answer,
            "error": self.error,
            "metadata": self.metadata
        }