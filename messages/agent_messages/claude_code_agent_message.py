"""
AutoGPTAgentMessage
"""

from messages.agent_messages.executor_agent_message import ExecutorAgentMessage


class ClaudeCodeMessage(ExecutorAgentMessage):
    """
    AgentMessage subclass for responses from the ClaudeCodeAgent.
    """

    def __init__(
        self,
        agent_id: str,
        message: str = None,
        prev: ExecutorAgentMessage = None,
        submission: bool = False,
    ) -> None:
        super().__init__(
            agent_id=agent_id, message=message, prev=prev, submission=submission
        )
