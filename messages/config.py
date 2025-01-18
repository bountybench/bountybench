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
        message_type_mapping = {
            'WorkflowMessage': MessageType.WORKFLOW,
            'PhaseMessage': MessageType.PHASE,
            'AgentMessage': MessageType.AGENT,
            'ActionMessage': MessageType.ACTION
        }
        return message_type_mapping.get(message_class.__name__, MessageType.ACTION).value

# Create a global instance of LoggingConfig
logging_config = LoggingConfig()

# Function to set logging level
def set_logging_level(level: MessageType):
    logging_config.set_level(level)

# Function to check if a message should be logged
def should_log(message) -> bool:
    return logging_config.should_log(type(message))