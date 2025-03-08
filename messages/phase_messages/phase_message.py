from typing import List, Optional

from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message

QUERY_TIME_TAKEN_IN_MS= "query_time_taken_in_ms"
INPUT_TOKEN = "input_token"
OUTPUT_TOKEN = "output_token"

class PhaseMessage(Message):
    def __init__(self, phase_id: str, prev: "PhaseMessage" = None) -> None:
        self._phase_id = phase_id
        self._success = False
        self._complete = False
        self._summary = "incomplete"
        self._agent_messages = []
        self._phase_summary = None
        self.usage = {INPUT_TOKEN: 0, OUTPUT_TOKEN: 0, QUERY_TIME_TAKEN_IN_MS: 0}
        super().__init__(prev)

    @property
    def phase_id(self) -> str:
        return self._phase_id

    @property
    def workflow_id(self) -> str:
        if self.parent:
            return self.parent.workflow_id
        return None

    @property
    def success(self) -> bool:
        return self._success

    @property
    def complete(self) -> bool:
        return self._complete

    @property
    def summary(self) -> bool:
        return self._summary

    @property
    def agent_messages(self) -> List[AgentMessage]:
        return self._agent_messages

    @property
    def phase_summary(self) -> str:
        return self.summary
    
    @property
    def phase_usage(self) -> str: 
        return self.usage

    @property
    def current_children(self) -> List[AgentMessage]:
        current_agents = []
        if len(self.agent_messages) > 0:
            current_message = self.agent_messages[0]
            current_message = current_message.get_latest_version()

            current_agents.append(current_message)
            while (
                current_message.next
                and current_message.next.prev
                and current_message.next.prev.id == current_message.id
            ):
                current_message = current_message.next
                current_message = current_message.get_latest_version()
                current_agents.append(current_message)

        return current_agents

    def set_success(self):
        self._success = True

    def set_complete(self):
        self._complete = True

    def set_summary(self, summary: str):
        self._summary = summary
    
    def set_token_usage(self,input_token:int, output_token:int):
        self.usage[INPUT_TOKEN] = input_token
        self.usage[OUTPUT_TOKEN] = output_token

    def increment_token_usage(self, increment_input: int, increment_output: int):
        self.usage[INPUT_TOKEN] += increment_input
        self.usage[OUTPUT_TOKEN] += increment_output
    
    def set_time_usage(self,time:float):
        self.usage[QUERY_TIME_TAKEN_IN_MS] = time

    def increment_time_usage(self, incrementTime: float):
        self.usage[QUERY_TIME_TAKEN_IN_MS] += incrementTime

    def add_child_message(self, agent_message: AgentMessage):
        self._agent_messages.append(agent_message)
        agent_message.set_parent(self)
        from messages.message_utils import log_message

        for action_message in agent_message.action_messages:
            log_message(action_message)
        log_message(agent_message)

    def to_broadcast_dict(self) -> dict:
        base_dict = super().to_broadcast_dict()
        broadcast_dict = {
            "phase_id": self.phase_id,
            "phase_summary": self.summary,
            "current_children": [
                agent_message.to_broadcast_dict()
                for agent_message in self.current_children
            ],
        }
        broadcast_dict.update(base_dict)
        return broadcast_dict

    def to_log_dict(self) -> dict:
        base_dict = super().to_log_dict()
        log_dict = {
            "phase_id": self.phase_id,
            "phase_summary": self.summary,
            "phase_usage": self.usage, 
            "success": self.success,
            "agent_messages": (
                [agent_message.to_log_dict() for agent_message in self.agent_messages]
                if self.agent_messages
                else None
            ),
        }
        log_dict.update(base_dict)
        return log_dict
