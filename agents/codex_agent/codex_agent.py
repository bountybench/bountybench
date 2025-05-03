import shlex
from typing import List

from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.error_action_message import ErrorActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.codex_agent_message import CodexMessage
from resources.resource_type import ResourceType


class CodexAgentConfig(AgentConfig):
    """Configuration for CodexAgent. No additional parameters required."""
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
        Execute Codex CLI with the prompt from the input message.

        Args:
            messages: List containing exactly one AgentMessage with the prompt.

        Returns:
            CodexMessage containing the Codex CLI output as a child ActionMessage.
        """
        if len(messages) != 1:
            raise ValueError(
                f"CodexAgent requires exactly one prompt message, got {len(messages)}"
            )
        
        prev_agent_message = messages[0]
        while hasattr(prev_agent_message, 'version_next') and prev_agent_message.version_next:
            prev_agent_message = prev_agent_message.version_next

        prompt = prev_agent_message.message or ""
        quoted_prompt = shlex.quote(prompt)
        
        cmd_parts = [
            "codex",
            "--quiet",
            "--json",
            "--approval-mode", "full-auto",
            quoted_prompt,
        ]
        cmd_str = "Command: " + " ".join(cmd_parts)

        cmd_msg = CommandMessage(
            resource_id=self.resources.kali_env.resource_id,
            message=cmd_str,
            prev=None,
        )
        agent_msg = CodexMessage(
            agent_id=self.agent_id,
            prev=prev_agent_message,
            submission=True,
        )
        try:
            output = self.resources.kali_env.run(cmd_msg)
            agent_msg.add_child_message(output)
        except Exception as e:
            err = ErrorActionMessage(
                resource_id=self.resources.kali_env.resource_id,
                message=str(e),
                error_type=type(e).__name__,
                prev=cmd_msg,
            )
            agent_msg.add_child_message(err)
        return agent_msg
