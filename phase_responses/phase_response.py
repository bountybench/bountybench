from typing import Any, Dict, List
from phase_responses.phase_response_interface import PhaseResponseInterface
from responses.response import Response

class PhaseResponse(PhaseResponseInterface):
    def __init__(self, success: bool, agent_responses: List[Response]) -> None:
        self._success = success
        self._agent_responses = agent_responses
    
    @property
    def success(self) -> bool:
        return self._success

    @property
    def agent_responses(self) -> List[Response]:
        return self._agent_responses

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "agent_responses": [agent_response.to_dict() for agent_response in self.agent_responses]
        }
