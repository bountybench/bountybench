from abc import ABC, abstractmethod
from typing import List

from agents.base_agent import BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.error_action_message import ErrorActionMessage


class CLIAgent(BaseAgent, ABC):
    """
    Abstract base class for agents that run CLI commands in a Kali environment.

    Subclasses must implement build_command and build_agent_message.
    """

    @abstractmethod
    def build_command(self, prev_agent_message: AgentMessage) -> str:
        """
        Construct the raw command string to execute in the Kali environment.

        Args:
            prev_agent_message: The previous agent message containing the prompt.

        Returns:
            A shell command string, including any necessary markers (e.g., 'Command:').
        """
        ...

    @abstractmethod
    def build_agent_message(self, prev_agent_message: AgentMessage) -> AgentMessage:
        """
        Create the AgentMessage instance to wrap the command execution results.

        Args:
            prev_agent_message: The previous agent message to attach as prev.

        Returns:
            An AgentMessage subclass representing this agent's response.
        """
        ...

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        # Ensure exactly one prompt message is provided
        if len(messages) != 1:
            raise ValueError(
                f"{self.__class__.__name__} requires exactly one prompt message, got {len(messages)}"
            )
        # Unwrap to the latest version of the prompt
        prev = messages[0]
        while hasattr(prev, "version_next") and prev.version_next:
            prev = prev.version_next

        cmd_str = self.build_command(prev)
        cmd_msg = CommandMessage(
            resource_id=self.resources.kali_env.resource_id,
            message=cmd_str,
            prev=None,
        )
        agent_msg = self.build_agent_message(prev)
        try:
            output = self.resources.kali_env.run(cmd_msg)
            agent_msg.add_child_message(output)
        except Exception as e:
            error = ErrorActionMessage(
                resource_id=self.resources.kali_env.resource_id,
                message=str(e),
                error_type=type(e).__name__,
                prev=cmd_msg,
            )
            agent_msg.add_child_message(error)
        return agent_msg
