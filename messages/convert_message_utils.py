from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage

def cast_action_to_command(action: ActionMessage) -> CommandMessage:
    """
    Casts an ActionMessage object to a CommandMessage object in place.
    
    This modifies the class of the given object instead of creating a new instance.
    
    Args:
        action (ActionMessage): The ActionMessage object to cast.

    Returns:
        CommandMessage: The same object, now treated as a CommandMessage.
    """
    if not isinstance(action, ActionMessage):
        raise TypeError("Object must be an instance of ActionMessage")

    # Change the object's class to CommandMessage
    action.__class__ = CommandMessage

    # Ensure required attributes for CommandMessage exist
    if not hasattr(action, "_command"):
        action._command = action.parse_command()

    return action