from responses.observation import Observation
from responses.executor_response_interface import ExecutorResponseInterface
from responses.command_response_interface import CommandResponseInterface
from responses.response import Response
from responses.action_response import ActionType

from typing import Optional

class SimpleExecutorResponse(Response, ExecutorResponseInterface, CommandResponseInterface):
    """
    A response that requires an action and response.
    Implements both command and answer parsing logic, and observation handling.
    """

    def __init__(self, response: str, observation: Optional[Observation] = None) -> None:
        self._response = response
        self._observation = observation
        self._action = None

        # Parse for the answer (answer is optional)
        self._answer = self.parse_field(self._response, "answer: ")
        if self._answer:
            self._action = ActionType.ANSWER
        # Parse for the command (command is option)
        self._command = self.parse_field(self._response, "command: ")
        if self._command:
            self._action = ActionType.COMMAND

        if not self._action:
            raise Exception("An action of either command or answer is required but was not found in the response.")


    @property
    def action(self) -> ActionType:
        return self._action
    
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