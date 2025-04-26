from typing import List, Optional

from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.message_dict import message_dict
from workflows.workflow_context import current_workflow_id

QUERY_TIME_TAKEN_IN_MS = "query_time_taken_in_ms"
INPUT_TOKEN = "input_token"
OUTPUT_TOKEN = "output_token"
TOTAL_ITERATION_TIME_MS = "total_iteration_time_ms"


class PhaseMessage(Message):
    def __init__(
        self,
        phase_id: str,
        max_iterations: int = None,
        phase_idx: int = None,
        prev: "PhaseMessage" = None,
    ) -> None:
        self._phase_id = phase_id
        self._max_iterations = max_iterations
        self._phase_idx = phase_idx
        self._success = False
        self._submit = False
        self._complete = False
        self._summary = "incomplete"
        self._agent_messages = []
        self._phase_summary = None
        self.usage = {
            INPUT_TOKEN: 0,
            OUTPUT_TOKEN: 0,
            QUERY_TIME_TAKEN_IN_MS: 0,
            TOTAL_ITERATION_TIME_MS: 0,
        }
        super().__init__(prev)

    def _set_parent_from_context(self):
        workflow_id = current_workflow_id.get()
        parent_id = workflow_id # note phase_message parent will be workflow_message

        if parent_id and workflow_id in message_dict:
            parent_message = message_dict[workflow_id][parent_id]
            parent_message.add_child_message(self)

    @property
    def phase_id(self) -> str:
        return self._phase_id

    @property
    def max_iterations(self) -> str:
        return self._max_iterations

    @property
    def phase_idx(self) -> str:
        return self._phase_idx

    @property
    def workflow_id(self) -> str:
        if self.parent:
            return self.parent.workflow_id
        return None

    @property
    def success(self) -> bool:
        return self._success

    @property
    def submit(self) -> bool:
        return self._submit

    @property
    def complete(self) -> bool:
        return self._complete

    @property
    def summary(self) -> bool:
        return self._summary

    @property
    def phase_usage(self) -> str:
        return self.usage

    @property
    def agent_messages(self) -> List[AgentMessage]:
        return self._agent_messages

    @property
    def phase_summary(self) -> str:
        return self.summary

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

    def set_submit(self):
        self._submit = True

    def set_complete(self):
        self._complete = True

    def set_summary(self, summary: str):
        self._summary = summary

    def add_child_message(self, agent_message: AgentMessage):
        self._agent_messages.append(agent_message)
        agent_message.set_parent(self)
        from messages.message_utils import log_message

        for action_message in agent_message.action_messages:
            log_message(action_message)
        log_message(agent_message)

    def calculate_total_usages(self):
        total_input_tokens = 0
        total_output_tokens = 0
        total_query_time_taken_in_ms = 0
        total_iteration_time_ms = 0

        for agent_message in self._agent_messages:
            total_iteration_time_ms += (
                agent_message.iteration_time_ms
                if agent_message.iteration_time_ms
                else 0
            )
            for action_message in agent_message._action_messages:
                metadata = action_message._additional_metadata
                if isinstance(metadata, tuple) and len(metadata) > 0:
                    metadata = metadata[0]  # Extract the dictionary from the tuple
                if isinstance(metadata, dict) and metadata:
                    # not all metadatas have token information
                    if all(
                        key in metadata
                        for key in ["input_tokens", "output_tokens", "time_taken_in_ms"]
                    ):
                        total_input_tokens += metadata["input_tokens"]
                        total_output_tokens += metadata["output_tokens"]
                        total_query_time_taken_in_ms += metadata["time_taken_in_ms"]

        self.usage = {
            INPUT_TOKEN: total_input_tokens,
            OUTPUT_TOKEN: total_output_tokens,
            QUERY_TIME_TAKEN_IN_MS: total_query_time_taken_in_ms,
            TOTAL_ITERATION_TIME_MS: total_iteration_time_ms,
        }

        return self.usage

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
        usage = self.calculate_total_usages()
        log_dict = {
            "phase_id": self.phase_id,
            "phase_idx": self.phase_idx,
            "phase_summary": self.summary,
            "phase_usage": usage,
            "success": self.success,
            "submit": self.submit,
            "max_iterations": self.max_iterations,
            "agent_messages": (
                [agent_message.to_log_dict() for agent_message in self.agent_messages]
                if self.agent_messages
                else None
            ),
        }
        log_dict.update(base_dict)
        return log_dict
