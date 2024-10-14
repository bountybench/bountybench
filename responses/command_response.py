from responses.command_response_interface import  CommandResponseInterface
from responses.parse_response import parse_field
from responses.observation import Observation

class CommandResponse(CommandResponseInterface):
    def __init__(self, response: str) -> None:
        self._response = response
        self._command = self.parse_command()
        self._observation = None
 
    @property
    def response(self) -> str:
        return self._response

    @property
    def command(self) -> str:
        return self._command
    
    def parse_command(self) -> str:
        command = parse_field(self._response, "Command: ")
        if not command:
            raise Exception("Command is missing from response, cannot be a command response.")
        return command
    
    @property
    def observation(self) -> str:
        if self._observation is None:
            raise Exception("Observation is missing or the command has not been executed yet.")
        return self._observation

    def set_observation(self, observation: Observation) -> None:
        self._observation = observation
        self._response += f"\nObservation: {observation.raw_output}"
