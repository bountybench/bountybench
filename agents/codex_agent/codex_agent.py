import shlex

from agents.base_agent import AgentConfig
from agents.cli_agent import CLIAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.codex_agent_message import CodexMessage
from resources.resource_type import ResourceType


class CodexAgentConfig(AgentConfig):
    """Configuration for CodexAgent. No additional parameters required."""
    pass


class CodexAgent(CLIAgent):
    """
    Agent that runs the OpenAI Codex CLI with a given prompt.

    Requires resources to initialize the bounty environment and codebase.
    """
    REQUIRED_RESOURCES = [
        ResourceType.INIT_FILES,
        ResourceType.KALI_ENV,
        ResourceType.MODEL,
    ]
    OPTIONAL_RESOURCES = [ResourceType.REPO_SETUP, ResourceType.BOUNTY_SETUP]
    ACCESSIBLE_RESOURCES = [ResourceType.KALI_ENV, ResourceType.MODEL]

    def build_command(self, prev_agent_message: AgentMessage) -> str:
        """
        Build the CLI command string for running OpenAI Codex.
        """
        prompt = prev_agent_message.message or ""
        quoted_prompt = shlex.quote(prompt)
        model = self.resources.model.model.replace("openai/", "")
        cmd_parts = [
            "codex",
            "--quiet",
            "--model",
            model,
            "--approval-mode",
            "full-auto",
            quoted_prompt,
        ]
        return "Command: " + " ".join(cmd_parts)

    def build_agent_message(self, prev_agent_message: AgentMessage) -> AgentMessage:
        """Instantiate the CodexMessage for this agent."""
        return CodexMessage(
            agent_id=self.agent_id,
            prev=prev_agent_message,
            submission=True,
        )
