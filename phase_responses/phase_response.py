from typing import Any, Dict, List
from phase_responses.phase_response_interface import PhaseResponseInterface
from responses.response import Response

class PhaseResponse(PhaseResponseInterface):
    def __init__(self, status: str, agent_responses: List[Response]):
        self._status = status
        self._agent_responses = agent_responses
    
    @property
    def status(self) -> str:
        return self._status

    @property
    def agent_responses(self) -> List[Response]:
        return self._agent_responses

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "agent_responses": [agent_response.to_dict() for agent_response in self.agent_responses]
        }
