from responses.command_response import SimpleCommandResponse
from responses.observation import Observation
from responses.executor_response_interface import ExecutorResponseInterface
from responses.command_response_interface import CommandResponseInterface
from responses.response import Response

from typing import Optional

class SimpleExecutorResponse(Response, ExecutorResponseInterface, CommandResponseInterface):
    """
    A response that requires a command and optionally an answer.
    Implements both command and answer parsing logic, and observation handling.
    """

    def __init__(self, response: str, observation: Optional[Observation] = None) -> None:
        self._response = response
        self._observation = observation

        # Parse for the command (command is required)
        self._command = self.parse_field(self._response, "command: ")
        if not self._command:
            raise Exception("Command is required but was not found in the response.")

        # Parse for the answer (answer is optional)
        self._answer = self.parse_field(self._response, "answer: ")

    @property
    def command(self) -> Optional[str]:
        return self._command

    @property
    def answer(self) -> Optional[str]:
        return self._answer

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