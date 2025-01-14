from typing import List
from agents.executor_agent.prompt import STOP_TOKEN
from messages.command_message_interface import  CommandMessageInterface
from messages.parse_message import parse_field
from messages.observation import Observation

class CommandMessage(CommandMessageInterface):
    def __init__(self, message: str) -> None:
        self._message = message
        self._command = self.parse_command()
        self._observation = None
 
    @property
    def message(self) -> str:
        return self._message

    @property
    def command(self) -> str:
        return self._command
    
    def parse_command(self) -> List[str]:
        command = parse_field(self._message, "Command:", stop_str=STOP_TOKEN)
        if not command:
            raise Exception("Command is missing from message, cannot be a command message.")
        return command
    
    @property
    def observation(self) -> str:
        if self._observation is None:
            raise Exception("Observation is missing or the command has not been executed yet.")
        return self._observation

    def set_observation(self, observation: Observation) -> None:
        self._observation = observation
        self._message += f"\nObservation: {observation.raw_output}"
    
    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "command": self.command,
            "observation": self.observation.raw_output
        }