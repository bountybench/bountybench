from responses.response import Response

class EditResponse(Response): 
    def __init__(self, response: str) -> None:
        self._response = response

    def add(self, text: str):
        self._response += text

    def edit(self, text: str):
        self._response = text

    @property
    def response(self) -> str:
        return self._response
    
    def to_dict(self) -> dict:
        return {
            "response": self.response
        }