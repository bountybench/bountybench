from responses.command_response import SimpleCommandResponse
from responses.observation import Observation
from responses.executor_response_interface import ExecutorResponseInterface
from responses.response import Response

from typing import Optional
from enum import Enum

class SimpleExecutorResponse(ExecutorResponseInterface):
    
    def __init__(self, response: str, observation: Optional[Observation] = None) -> None:
        # SimpleExecutorResponse needs either an answer or a command        
        self._type = None  # Flag indicating whether it's an answer or command

        # First try to parse for an answer
        self._answer = self.parse_answer(response)
        if self._answer:
            self._type = "answer"
        else:
            try:
                self._command = SimpleCommandResponse(response).command
                self._type = "command"
            except Exception as e:
                # If neither answer nor command is found, raise an exception
                raise Exception("Neither command nor answer found in the response.") from e
        
        self._response = response
        self._observation = observation

    @property
    def command(self) -> Optional[str]:
        """
        Return the parsed command (if present).
        """
        return self._command

    @property
    def answer(self) -> Optional[str]:
        """
        Return the parsed answer (if present).
        """
        return self._answer

    @property
    def response_type(self) -> Optional[str]:
        """
        Return the type of the response ('command' or 'answer').
        """
        return self._type
    
    @property
    def response(self) -> str:
        return self._response

    @property
    def observation(self) -> Optional[str]:
        if self._observation is None:
            raise Exception("Observation is missing or the command has not been executed yet.")
        return self._observation

    def set_observation(self, observation: str) -> None:
        self._observation = observation

    def parse_answer(self, response: str) -> Optional[str]:
        # Use the existing parse_field to extract the answer
        answer = Response.parse_field(response, "answer: ")
        return answer if answer else None