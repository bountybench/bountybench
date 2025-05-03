import shlex

from agents.base_agent import AgentConfig
from agents.cli_agent import CLIAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.claude_code_agent_message import ClaudeCodeMessage
from prompts.prompts import STOP_TOKEN
from resources.resource_type import ResourceType


class ClaudeCodeAgentConfig(AgentConfig):
    """Configuration for ClaudeCodeAgentConfig. No additional parameters."""

    pass


class ClaudeCodeAgent(CLIAgent):
    """
    Agent that runs the Claude Code with a given prompt.

    Requires resources to initialize the bounty environment and codebase.
    """

    REQUIRED_RESOURCES = [
        ResourceType.INIT_FILES,
        ResourceType.KALI_ENV,
    ]
    OPTIONAL_RESOURCES = [ResourceType.REPO_SETUP, ResourceType.BOUNTY_SETUP]
    ACCESSIBLE_RESOURCES = [ResourceType.KALI_ENV]

    def build_command(self, prev_agent_message: AgentMessage) -> str:
        """
        Build the CLI command string for running Claude Code.
        """
        prompt = prev_agent_message.message or ""
        quoted_prompt = shlex.quote(prompt)
        tools = (
            "Bash,Edit,Write,Agent,Glob,Grep,LS,Read,NotebookEdit,NotebookRead,WebFetch"
        )
        quoted_tools = shlex.quote(tools)
        
        return (
            f"Command: claude -d -p {quoted_prompt} --output-format json "
            f"--verbose --allowedTools {quoted_tools}\n{STOP_TOKEN}"
        )

    def build_agent_message(self, prev_agent_message: AgentMessage) -> AgentMessage:
        """Instantiate the ClaudeCodeMessage for this agent."""
        return ClaudeCodeMessage(
            agent_id=self.agent_id,
            prev=prev_agent_message,
            submission=True,
        )
