from enum import Enum
from typing import Type


class MessageType(Enum):
    WORKFLOW = 0
    PHASE = 1
    AGENT = 2
    ACTION = 3


class LoggingConfig:
    def __init__(self):
        self.current_level = MessageType.ACTION

    def set_level(self, level: MessageType):
        self.current_level = level

    def should_log(self, message_class: Type):
        message_level = self.get_message_level(message_class)
        return message_level <= self.current_level.value

    @staticmethod
    def get_message_level(message_class: Type) -> int:
        from messages.action_messages.action_message import ActionMessage
        from messages.agent_messages.agent_message import AgentMessage
        from messages.phase_messages.phase_message import PhaseMessage
        from messages.workflow_message import WorkflowMessage

        if not isinstance(message_class, type):
            raise TypeError("message_class must be a type")

        if issubclass(message_class, WorkflowMessage):
            return MessageType.WORKFLOW.value
        elif issubclass(message_class, PhaseMessage):
            return MessageType.PHASE.value
        elif issubclass(message_class, AgentMessage):
            return MessageType.AGENT.value
        elif issubclass(message_class, ActionMessage):
            return MessageType.ACTION.value
        else:
            print(
                f"Unknown message class: {message_class.__name__}. Defaulting to ACTION level."
            )
            return MessageType.ACTION.value


# Create a global instance of LoggingConfig
logging_config = LoggingConfig()


# Function to set logging level
def set_logging_level(level: MessageType):
    logging_config.set_level(level)


# Function to check if a message should be logged
def should_log(message) -> bool:
    return logging_config.should_log(type(message))
