from typing import List, Optional

from messages.action_messages.action_message import ActionMessage
from messages.message import Message


class AgentMessage(Message):

    def __init__(
        self,
        agent_id: str,
        message: Optional[str] = "",
        prev: "AgentMessage" = None,
    ) -> None:
        self._message = message
        self._iteration = None
        self._agent_id = agent_id
        self._action_messages = []
        self._memory = None
        super().__init__(prev=prev)

    @property
    def message(self) -> str:
        return self._message

    def set_message(self, value: str):
        """
        Setter for message property.
        """
        self._message = value

    @property
    def iteration(self) -> int:
        return self._iteration

    def set_iteration(self, iteration: int) -> None:
        self._iteration = iteration

    @property
    def message_type(self) -> str:
        """
        Override the message_type property to always return "AgentMessage"
        for AgentMessage and its subclasses.
        """
        return "AgentMessage"

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def workflow_id(self) -> str:
        if self.parent:
            return self.parent.workflow_id
        return None

    @property
    def action_messages(self) -> List[ActionMessage]:
        return self._action_messages

    @property
    def current_children(self) -> List[ActionMessage]:
        current_actions = []
        if len(self.action_messages) > 0:
            current_message = self.action_messages[0]
            current_message = current_message.get_latest_version()

            current_actions.append(current_message)
            while (
                current_message.next
                and current_message.next.prev
                and current_message.next.prev.id == current_message.id
            ):
                current_message = current_message.next
                current_message = current_message.get_latest_version()
                current_actions.append(current_message)

        return current_actions

    @property
    def memory(self):
        return self._memory

    @memory.setter
    def memory(self, x: str):
        """This should only be set by the MemoryResource."""
        self._memory = x

    def add_child_message(self, action_message: ActionMessage):
        self._action_messages.append(action_message)
        action_message.set_parent(self)
        from messages.message_utils import log_message

        log_message(action_message)
        log_message(self)

    def to_broadcast_dict(self) -> dict:
        base_dict = super().to_broadcast_dict()
        broadcast_dict = {
            "agent_id": self.agent_id,
            "message": self.message,
            "current_children": [
                action_message.to_broadcast_dict()
                for action_message in self.current_children
            ],
            "iteration": self.iteration,
        }
        broadcast_dict.update(base_dict)
        return broadcast_dict

    def to_log_dict(self) -> dict:
        base_dict = super().to_log_dict()
        log_dict = {
            "agent_id": self.agent_id,
            "message": self.message,
            "action_messages": (
                [
                    action_message.to_log_dict()
                    for action_message in self.action_messages
                ]
                if self.action_messages
                else None
            ),
        }
        log_dict.update(base_dict)
        return log_dict

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        """Reconstruct an agent message from its dictionary representation"""
        agent_id = data.get("agent_id")
        message = data.get("message", "")

        if cls == AgentMessage:
            # Determine the correct message class based on agent_id
            if agent_id == "exploit_agent":
                from messages.agent_messages.exploit_agent_message import (
                    ExploitAgentMessage,
                )

                return ExploitAgentMessage.from_dict(data)
            elif agent_id == "patch_agent":
                from messages.agent_messages.patch_agent_message import (
                    PatchAgentMessage,
                )

                return PatchAgentMessage.from_dict(data)

        agent_message = cls(agent_id=agent_id, message=message)

        # Set base Message properties
        agent_message._id = data.get("current_id")
        agent_message.timestamp = data.get("timestamp")

        # Handle prev/next relationships
        if "prev" in data:
            agent_message._prev = data.get("prev")
        if "next" in data:
            agent_message._next = data.get("next")

        return agent_message
