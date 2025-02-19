from agents.prompts import STOP_TOKEN
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.answer_message import AnswerMessage
from messages.parse_message import extract_command, extract_answer

def cast_action_to_command(action: ActionMessage) -> CommandMessage:
    """
    Casts an ActionMessage object to a CommandMessage object in place.
    Casts an ActionMessage object to a CommandMessage object in place.
    
    This modifies the class of the given object instead of creating a new instance.
    
    Args:
        action (ActionMessage): The ActionMessage object to cast.

    Returns:
        CommandMessage: The same object, now treated as a CommandMessage.
    """
    
    command = extract_command(action.message, STOP_TOKEN)

    # If extraction is successful, cast the instance by reassigning its __class__.
    action.__class__ = CommandMessage
    action._command = command
    return action

def cast_action_to_answer(action: ActionMessage) -> AnswerMessage:

    answer = extract_answer(action.message, STOP_TOKEN)

    action.__class__ = AnswerMessage
    action._answer = answer
    return action
