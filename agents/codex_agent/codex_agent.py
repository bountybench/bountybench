"""
Agent implementing OpenAI Codex CLI workflow.
"""

import shlex
from typing import List

from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.codex_agent_message import CodexAgentMessage
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.error_action_message import ErrorActionMessage
from messages.agent_messages.agent_message import AgentMessage
from resources.resource_type import ResourceType


class CodexAgentConfig(AgentConfig):
    """Configuration for CodexAgent. No additional parameters."""
    pass


class CodexAgent(BaseAgent):
    """
    Agent that runs the OpenAI Codex CLI with a given prompt.
    Requires resources to initialize the bounty environment and codebase.
    """

    REQUIRED_RESOURCES = [
        ResourceType.INIT_FILES,
        ResourceType.KALI_ENV,
    ]
    OPTIONAL_RESOURCES = [ResourceType.REPO_SETUP, ResourceType.BOUNTY_SETUP]
    ACCESSIBLE_RESOURCES = [ResourceType.KALI_ENV]

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        """
        Execute the Codex CLI with the prompt from the initial message.
        Args:
            messages: List containing exactly one AgentMessage with the prompt.
        Returns:
            AgentMessage containing the Codex CLI output as a child ActionMessage.
        """
        if len(messages) != 1:
            raise ValueError(
                f"CodexAgent requires exactly one prompt message, got {len(messages)}"
            )
        # Use the latest version of the input message
        prev_agent_message = messages[0]
        while prev_agent_message.version_next:
            prev_agent_message = prev_agent_message.version_next

        prompt = prev_agent_message.message or ""
        # Quote prompt for safe shell execution
        quoted_prompt = shlex.quote(prompt)
        # Construct Codex CLI command: full-auto, quiet mode
        cmd_str = f"codex -a full-auto --quiet {quoted_prompt}"

        cmd_msg = CommandMessage(
            resource_id=self.resources.kali_env.resource_id,
            message=cmd_str,
            prev=None,
        )
        # Initialize agent message with success=False by default
        agent_message = CodexAgentMessage(
            agent_id=self.agent_id,
            message=None,
            success=False,
            prev=prev_agent_message,
        )
        try:
            # Run the command in Kali environment
            output = self.resources.kali_env.run(cmd_msg)
            agent_message.add_child_message(output)
            # Mark as successful if no exception
            agent_message.set_success(True)
        except Exception as e:
            error = ErrorActionMessage(
                resource_id=self.resources.kali_env.resource_id,
                message=str(e),
                error_type=type(e).__name__,
                prev=cmd_msg,
            )
            agent_message.add_child_message(error)
            agent_message.set_success(False)
        return agent_message