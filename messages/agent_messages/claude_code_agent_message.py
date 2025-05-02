"""
AutoGPTAgentMessage
"""

from messages.agent_messages.agent_message import AgentMessage


class ClaudeCodeMessage(AgentMessage):
    """
    AgentMessage subclass for responses from the ClaudeCodeAgent.
    """

    def __init__(
        self,
        agent_id: str,
        message: str = None,
        prev: AgentMessage = None,
    ) -> None:
        super().__init__(agent_id=agent_id, message=message, prev=prev)
