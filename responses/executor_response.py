from responses.command_response import SimpleCommandResponse
from observation import Observation

from typing import Optional

class SimpleExecutorResponse:
    
    def __init__(self, response: str, observation: Optional[Observation] = None) -> None:
        self._response = response
        self._command = SimpleCommandResponse(response).command
        self._observation = observation

    @property
    def command(self) -> str:
        """
        Return the command extracted from the response.
        """
        return self._command

    @property
    def observation(self) -> Observation:
        """
        Return the observation object (after execution).
        """
        if self._observation is None:
            raise Exception("Observation is missing or the command has not been executed yet.")
        return self._observation

    def set_observation(self, observation: Observation) -> None:
        """
        Set the observation after the command has been executed.
        """
        self._observation = observation