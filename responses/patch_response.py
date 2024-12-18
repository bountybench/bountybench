from responses.response import Response

class PatchResponse(Response): 
    def __init__(self, response: str) -> None:
        self._response = response

    @property
    def response(self) -> str:
        return self._response
    
    def to_dict(self) -> dict:
        return {
            "response": self.response
        }