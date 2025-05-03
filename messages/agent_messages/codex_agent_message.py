"""
CodexAgentMessage
"""

from messages.agent_messages.agent_message import AgentMessage


class CodexAgentMessage(AgentMessage):
    """
    AgentMessage subclass for responses from the CodexAgent.
    """
    def __init__(
        self,
        agent_id: str,
        message: str = None,
        success: bool = False,
        prev: AgentMessage = None,
    ) -> None:
        super().__init__(agent_id=agent_id, message=message, prev=prev)
        self._success = success

    @property
    def success(self) -> bool:
        return getattr(self, '_success', False)

    def set_success(self, value: bool) -> None:
        self._success = value

    def to_broadcast_dict(self) -> dict:
        base_dict = super().to_broadcast_dict()
        base_dict.update({'success': self.success})
        return base_dict

    def to_log_dict(self) -> dict:
        base_dict = super().to_log_dict()
        base_dict.update({'success': self.success})
        return base_dict