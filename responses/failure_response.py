from responses.response import Response


class FailureResponse(Response):
    def __init__(self, response: str) -> None:
        self._failure_reason = response
        self._response = "Failure Response"
 
    @property
    def response(self) -> str:
        return self._response
    
    @property
    def failure_reason(self) -> str:
        return self._failure_reason
    
    def to_dict(self) -> dict:
        return {
            "response": self.response,
            "failure_reason": self.failure_reason
        }