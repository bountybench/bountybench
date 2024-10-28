from typing import Any, Dict
from responses.extraction_response_interface import ExtractionResponseInterface

class ExtractionResponse(ExtractionResponseInterface):
    def __init__(self, response: str, proof: str, metadata: Dict[str, Any]) -> None:
        self._response = response
        self._proof = proof
        self._metadata = metadata
 
    @property
    def response(self) -> str:
        return self._response
    
    @property
    def proof(self) -> str:
        return self._proof
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata
