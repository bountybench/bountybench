from responses.patch_response_interface import  PatchResponseInterface

class PatchResponse(PatchResponseInterface):
    def __init__(self, response: str) -> None:
        self._response = response
 
    @property
    def response(self) -> str:
        return self._response