import inspect
from dataclasses import dataclass, field
from functools import partial
from typing import Callable, List

from messages.agent_messages.agent_message import ActionMessage, AgentMessage
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.memory_resource.memory_function import (
    MemoryCollationFunctions,
    MemoryTruncationFunctions,
)
from resources.memory_resource.memory_prompt import MemoryPrompts
from resources.memory_resource.memory_scope import MemoryScope
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


@dataclass
class MemoryResourceConfig(BaseResourceConfig):
    """Configuration for MemoryResource"""

    scope: MemoryScope = field(default=MemoryScope.WORKFLOW)
    fmt: str = field(default=MemoryPrompts.DEFAULT_FMT_WORKFLOW)
    collate_fn: Callable[[List], str] = field(
        default=MemoryCollationFunctions.collate_ordered
    )
    segment_trunc_fn: Callable[[List], List] = field(
        default=partial(MemoryTruncationFunctions.segment_fn_last_n, n=9)
    )
    memory_trunc_fn: Callable[[List], List] = field(
        default=MemoryTruncationFunctions.memory_fn_by_message_token
    )

    def validate(self) -> None:
        """Validate LLMResource configuration"""
        MemoryPrompts.validate_memory_prompt(self.fmt, self.scope)
        MemoryCollationFunctions.validate_collation_fn(self.collate_fn)


class MemoryResource(BaseResource):
    """Memory Resource"""

    def __init__(self, resource_id: str, config: MemoryResourceConfig):
        super().__init__(resource_id, config)
        self.scope = self._resource_config.scope

        self.stop_cls = [WorkflowMessage, PhaseMessage, AgentMessage][self.scope.value]

        self.message_hierarchy = {
            WorkflowMessage: PhaseMessage,
            PhaseMessage: AgentMessage,
            AgentMessage: ActionMessage,
            ActionMessage: ActionMessage,
        }

        self.fmt = self._resource_config.fmt

        self.collate_fn = self._resource_config.collate_fn

        self.segment_trunc_fn = self._resource_config.segment_trunc_fn
        self.memory_trunc_fn = self._resource_config.memory_trunc_fn

    def parse_message(self, message: ActionMessage | AgentMessage | PhaseMessage):
        """Given a message, parse into prev_{phase | agent | action} messages.

        Example traversal if scope is workflow, and given message is action_message
          1) go up to workflow message, then do a pre-order traversal,
             stopping at phase_message that contains the action message
          2) go up to that phase_message, then do a pre-order traversal,
             stopping at agent_message that contains the action message
          3) go up to that agent_message, then do a pre-order traversal,
             stopping at given action message

        This way, we can segment memory into prev_phase, prev_agent, and prev_action
        """
        assert isinstance(
            message, (ActionMessage, AgentMessage, PhaseMessage)
        ), f"Invalid message type {type(message)} passed to memory"

        stop_cls = self.stop_cls
        segments = []

        # collect system messages (initial_prompts) separately
        system_messages = set()
        while not isinstance(message, stop_cls):
            root, down_stop = self.go_up(message, stop_cls)
            segments.append(
                self.go_down(
                    root, sys_messages=system_messages, stop_instance=down_stop
                )
            )
            stop_cls = self.message_hierarchy[stop_cls]

        if self.is_initial_prompt(message):
            system_messages.add(message._message)
        else:
            if hasattr(message, "_message") and message._message:
                self.add_to_segment(message, segments[-1])

        # truncate each segment
        trunc_segments = [
            self.segment_trunc_fn(x, self.pinned_messages) for x in segments
        ]
        # truncate all memory
        trunc_segments = self.memory_trunc_fn(trunc_segments, self.pinned_messages)
        start = 1
        collated_segments = []
        for segment in trunc_segments:
            collated_segment = self.collate_fn(segment, start=start)
            collated_segments.append(collated_segment)
            start += len(segment)
        trunc_segments = collated_segments

        return trunc_segments, system_messages

    def get_memory(self, message: ActionMessage | AgentMessage | PhaseMessage):
        messages, system_messages = self.parse_message(message)

        assert len(system_messages) == 1, (
            f"Current memory implementation only supports single initial prompt.\n"
            f"Found {len(system_messages)} initial prompts (system messages)"
            + f":\n\t{[msg[:25] + '...' for msg in system_messages]}\n"
            if system_messages
            else ""
        )

        system_message = system_messages.pop()

        kwargs = ["prev_phase_messages", "prev_agent_messages", "prev_action_messages"][
            self.scope.value :
        ]

        assert len(messages) <= len(kwargs)

        while len(messages) < len(kwargs):
            messages.append("")

        # Only include sections that have content
        non_empty_sections = [(k, m) for k, m in zip(kwargs, messages) if m]

        if not non_empty_sections:
            # If no messages present, only include system message
            message.memory = system_message
            return message

        # Format memory string with only non-empty sections
        memory_sections = [f"{m}" for _, m in non_empty_sections]
        memory_str = (
            f"{MemoryPrompts._DEFAULT_SEGUE}\n" f"{chr(10).join(memory_sections)}"
        )

        message.memory = f"{system_message}\n\n{memory_str}"
        return message

    def stop(self):
        logger.debug(
            f"Stopping Memory resource {self.resource_id} (no cleanup required)"
        )

    def to_dict(self) -> dict:
        """
        Serializes the MemoryResource state to a dictionary.
        """

        def get_function_repr(func):
            """Helper to get string representation of a function, handling partial functions."""
            if isinstance(func, partial):
                # For partial functions, get the name of the original function
                base_func = func.func
                base_name = (
                    base_func.__name__
                    if hasattr(base_func, "__name__")
                    else str(base_func)
                )
                return f"partial({base_name}){inspect.signature(func)}"
            else:
                # For regular functions
                return f"{func.__name__}{inspect.signature(func)}"

        return {
            "resource_id": self.resource_id,
            "collate_fn": get_function_repr(self._resource_config.collate_fn),
            "segment_trunc_fn": get_function_repr(
                self._resource_config.segment_trunc_fn
            ),
            "memory_trunc_fn": get_function_repr(self._resource_config.memory_trunc_fn),
            "scope": self._resource_config.scope.name,
        }

    def is_initial_prompt(self, msg_node):
        return isinstance(msg_node, AgentMessage) and msg_node.agent_id == "system"

    def extract_children(self, msg_node):
        if hasattr(msg_node, "_phase_messages"):
            return msg_node._phase_messages
        elif hasattr(msg_node, "_agent_messages"):
            return msg_node._agent_messages
        elif hasattr(msg_node, "_action_messages"):
            return msg_node._action_messages
        return []

    def extract_id(self, msg_node):
        if hasattr(msg_node, "_phase_messages"):
            return msg_node.workflow_id
        elif hasattr(msg_node, "_agent_messages"):
            return msg_node.phase_id
        elif hasattr(msg_node, "_action_messages"):
            return msg_node.agent_id

        assert isinstance(msg_node, ActionMessage)

        if msg_node.parent.agent_id == msg_node.resource_id:
            return msg_node.parent.agent_id
        return msg_node.parent.agent_id + "/" + msg_node.resource_id.split("_")[0]

    def add_to_segment(self, msg_node, segment):
        id_ = self.extract_id(msg_node)

        segment.append(f"[{id_}] {msg_node._message.strip()}")

    def go_up(self, msg_node, dst_cls):
        down_stop = None
        while not isinstance(msg_node, dst_cls):
            down_stop = msg_node
            msg_node = msg_node.parent
        return msg_node, down_stop

    def go_down(self, msg_node, sys_messages, stop_instance):
        if self.is_initial_prompt(msg_node):
            sys_messages.add(msg_node._message)
            return []

        children = self.extract_children(msg_node)

        # pre-order traversal
        segment = []
        if hasattr(msg_node, "_message"):
            # if AgentMessage has action messages, don't add agent._message
            # this is to avoid duplicates, as agent._message will include
            # all action messages otherwise
            if (
                not isinstance(msg_node, AgentMessage)
                or msg_node.agent_id != "executor_agent"
            ):
                self.add_to_segment(msg_node, segment)

        if len(children) > 0:
            if (
                isinstance(msg_node, AgentMessage)
                and msg_node.agent_id != "executor_agent"
            ):
                return segment
            child = children[0].get_latest_version()
            while child.next:
                if child is stop_instance:
                    break
                segment.extend(self.go_down(child, sys_messages, stop_instance))
                child = child.next.get_latest_version()

            if child is not stop_instance:
                segment.extend(self.go_down(child, sys_messages, stop_instance))

        return segment
