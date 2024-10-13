
class NullResponse(ResponseInterface):
    def __init__(self, response: str) -> None:
        self._response = ''
 
    @property
    def response(self) -> str:
        return self._response
