from typing import Optional
from messages.agent_messages.agent_message import AgentMessage


class ExecutorAgentMessage(AgentMessage):
    def __init__(
        self,
        agent_id: str,
        message: Optional[str] = None,
        submission: bool = False,
        prev: AgentMessage = None,
    ) -> None:
        super().__init__(agent_id=agent_id, message=message, prev=prev)
        self._submission = submission

    @property
    def submission(self) -> bool:
        return self._submission

    def set_submission(self, value: bool):
        self._submission = value

    def to_broadcast_dict(self) -> dict:
        base_dict = super().to_broadcast_dict()
        base_dict.update(
            {
                "submission": self.submission,
            }
        )
        return base_dict

    def to_log_dict(self) -> dict:
        base_dict = super().to_log_dict()
        base_dict.update(
            {
                "submission": self.submission,
            }
        )
        return base_dict
