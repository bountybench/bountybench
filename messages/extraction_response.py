from typing import Any, Dict
from responses.extraction_response_interface import ExtractionResponseInterface

class ExtractionResponse(ExtractionResponseInterface):
    def __init__(self, response: str, description: str, proof: str, bug_commit: str, bug_tag: str, patch_commit: str, patch_tag: str, metadata: Dict[str, Any], link: str) -> None:
        self._response = response
        self._description = description
        self._proof = proof
        self._bug_commit = bug_commit
        self._bug_tag = bug_tag
        self._patch_commit = patch_commit
        self._patch_tag = patch_tag
        self._metadata = metadata
        self._link = link

        if not self._bug_commit and not self._bug_tag:
            raise ValueError("Either bug_commit or bug_tag must be provided.")
 
    @property
    def response(self) -> str:
        return self._response
    
    @property
    def description(self) -> str:
        return self._description

    @property
    def proof(self) -> str:
        return self._proof
    
    @property
    def bug_commit(self) -> str:
        return self._bug_commit
    
    @property
    def bug_tag(self) -> str:
        return self._bug_tag
    
    @property
    def patch_commit(self) -> str:
        return self._patch_commit
    
    @property
    def patch_tag(self) -> str:
        return self._patch_tag

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata
    
    @property
    def link(self) -> str:
        return self._link
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self._response,
            "description": self._description,
            "proof": self._proof,
            "bug_commit": self._bug_commit,
            "bug_tag": self._bug_tag,
            "patch_commit": self._patch_commit,
            "patch_tag": self._patch_tag,
            "metadata": self._metadata,
            "link": self._link
        }
