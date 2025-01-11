from typing import Any, Dict, List
from phase_responses.phase_response_interface import PhaseResponseInterface
from responses.response import Response

class PhaseResponse(PhaseResponseInterface):
    def __init__(self, agent_responses: List[Response]) -> None:
        self._success = False
        self._complete = False
        self._agent_responses = agent_responses
    
    @property
    def success(self) -> bool:
        return self._success
    
    @property
    def complete(self) -> bool:
        return self._complete
    
    @property
    def agent_responses(self) -> List[Response]:
        return self._agent_responses

    def set_success(self):
        self._success = True

    def set_complete(self):
        self._complete = True

    def add_agent_response(self, agent_response: Response):
        self._agent_responses.append(agent_response)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "complete": self.complete,
            "agent_responses": [agent_response.to_dict() for agent_response in self.agent_responses]
        }
