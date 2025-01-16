from typing import List
from agents.prompts import STOP_TOKEN
from messages.action_messages.action_message import ActionMessage
from messages.parse_message import parse_field
from messages.observation import Observation

class CommandActionMessage(ActionMessage):

    def __init__(self, message: str, resource_id: str, prev: ActionMessage = None) -> None:
        super().__init__(message, prev, resource_id)
        self._command = self.parse_command()

    @property
    def command(self) -> str:
        return self._command
    
    def parse_command(self) -> List[str]:
        command = parse_field(self._message, "Command:", stop_str=STOP_TOKEN)
        if not command:
            raise Exception("Command is missing from message, cannot be a command message.")
        return command

    def to_dict(self) -> dict:
        base_dict = super().to_dict()        
        base_dict.update({
            "command": self.response
        })
        return base_dict