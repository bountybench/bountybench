from typing import List
from agents.prompts import STOP_TOKEN
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message_interface import  CommandMessageInterface
from messages.parse_message import parse_field

from typing import Dict, Any, Optional
    
class CommandMessage(CommandMessageInterface, ActionMessage):
    def __init__(self, resource_id: str, message: str, additional_metadata: Optional[Dict[str, Any]] = {}, prev: 'ActionMessage' = None, input_str: Optional[str] = None) -> None:
        self._message = message
        self._command = self.parse_command()
        super().__init__(resource_id, message, additional_metadata, prev, input_str)
        
    @property
    def command(self) -> str:
        return self._command
    
    def parse_command(self) -> List[str]:
        command = parse_field(self._message, "Command:", stop_str=STOP_TOKEN)
        if not command:
            raise Exception("Command is missing from message, cannot be a command message.")
        return command
    
    def to_dict(self) -> dict:
        action_dict = self.action_dict()
        action_dict.update({
            "command": self.command
        })
        base_dict = super(ActionMessage, self).to_dict() 
        action_dict.update(base_dict)
        return action_dict