from responses.response import Response


class GeneralResponse(Response):
    def __init__(self, response: str) -> None:
        self._response = response
 
    @property
    def response(self) -> str:
        return self._response