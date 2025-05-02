"""
Agent implementing an AutoGPT workflow.
"""

import shlex
from typing import List

from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.error_action_message import ErrorActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.claude_code_agent_message import ClaudeCodeMessage
from resources.resource_type import ResourceType


class ClaudeCodeAgentConfig(AgentConfig):
    """Configuration for ClaudeCodeAgentConfig. No additional parameters."""

    pass


class ClaudeCodeAgent(BaseAgent):
    """
    Agent that runs the Claude Code with a given prompt.

    Requires resources to initialize the bounty environment and codebase.
    """

    REQUIRED_RESOURCES = [
        ResourceType.INIT_FILES,
        ResourceType.KALI_ENV,
        ResourceType.REPO_SETUP,
        ResourceType.BOUNTY_SETUP,
    ]
    OPTIONAL_RESOURCES: List[ResourceType] = []
    ACCESSIBLE_RESOURCES = REQUIRED_RESOURCES

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        """
        Execute Claude Code with the prompt from the initial message.

        Args:
            messages: List containing exactly one AgentMessage with the prompt.

        Returns:
            AgentMessage containing the Claude Code output as a child ActionMessage.
        """
        if len(messages) != 1:
            raise ValueError(
                f"Claude Code Agent requires exactly one prompt message, got {len(messages)}"
            )
        # Use the latest version of the input message
        prev_agent_message = messages[0]
        while prev_agent_message.version_next:
            prev_agent_message = prev_agent_message.version_next

        prompt = prev_agent_message.message or ""
        # Quote the prompt and tools for safe shell execution
        quoted_prompt = shlex.quote(prompt)
        tools = (
            "Bash,Edit,Write,Agent,Glob,Grep,LS,Read,NotebookEdit,NotebookRead,WebFetch"
        )
        quoted_tools = shlex.quote(tools)
        cmd_str = f"claude -p {quoted_prompt} --allowedTools {quoted_tools} --output-format stream-json"

        cmd_msg = CommandMessage(
            resource_id=self.resources.kali_env.resource_id,
            message=cmd_str,
            prev=None,
        )
        agent_message = ClaudeCodeMessage(
            agent_id=self.agent_id,
            prev=prev_agent_message,
        )
        try:
            output = self.resources.kali_env.run(cmd_msg)
            agent_message.add_child_message(output)
        except Exception as e:
            error = ErrorActionMessage(
                resource_id=self.resources.kali_env.resource_id,
                message=str(e),
                error_type=type(e).__name__,
                prev=cmd_msg,
            )
            agent_message.add_child_message(error)
        return agent_message
