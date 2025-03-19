import inspect
import string
from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from typing import Callable, List

from messages.agent_messages.agent_message import ActionMessage, AgentMessage
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from resources.base_resource import BaseResource, BaseResourceConfig
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class MemoryScope(Enum):
    """
    Memory scope.
     - WORKFLOW: memory contains messages across a single workflow
     - PHASE: memory contains messages across a single phase
     - AGENT: memory contains messages across a single agent
    """

    WORKFLOW = 0
    PHASE = 1
    AGENT = 2


class MemoryPrompts:
    """Collection of format strings to convert memory to prompt."""

    _DEFAULT_SEGUE = (
        "In addition to the above task, "
        "you are also provided the transaction history of the system.\n"
        "You should account for previous messages (if present) "
        "that have occurred when formulating your response:"
    )

    _DEFAULT_SEGMENTS = (
        " * {prev_phase_messages}\n"
        " * {prev_agent_messages}\n"
        " * {prev_action_messages}"
    )

    DEFAULT_FMT_WORKFLOW = "\n".join([_DEFAULT_SEGUE, _DEFAULT_SEGMENTS])
    DEFAULT_FMT_PHASE = "\n".join(
        [_DEFAULT_SEGUE, "\n".join(_DEFAULT_SEGMENTS.split("\n")[1:])]
    )
    DEFAULT_FMT_AGENT = "\n".join(
        [_DEFAULT_SEGUE, "\n".join(_DEFAULT_SEGMENTS.split("\n")[2:])]
    )

    @staticmethod
    def validate_memory_prompt(prompt, scope: MemoryScope):
        kwargs = ["prev_phase_messages", "prev_agent_messages", "prev_action_messages"][
            scope.value :
        ]
        kwargs = set(kwargs)

        user_keys = set(
            x[1] for x in string.Formatter().parse(prompt) if x[1] is not None
        )

        if user_keys != kwargs:
            diffs = (user_keys - kwargs) | (kwargs - user_keys)
            raise ValueError(
                f"Format string does not match expected input for {str(scope)}\n"
                f"Expected format string kwargs: {kwargs}\n"
                f"Inputted format string kwargs: {user_keys}\n"
                f"Mismatched kwargs: {diffs}"
            )


class MemoryCollationFunctions:
    """
    Collection of memory collation functions.

    Collation functions should take a list of messages of a single segment,
    e.g., prev_agent_messages, and convert it into a single string.
    Each memory can have up to three segments, as defined in MemoryPrompts.
    """

    @staticmethod
    def collate_ordered(segment, start=1):
        """Join each message and prepend enumeration."""
        return "\n".join(f"{i+start}) {message}" for i, message in enumerate(segment))

    @staticmethod
    def validate_collation_fn(fn):
        assert (
            type(fn(["msg1", "msg2"])) == str
        ), "Memory collation_fn should take list of messages and output str."


class MemoryTruncationFunctions:
    """
    Collection of memory truncation functions.

    There are two types of truncation functions.
     - segment_fn*: Takes a list of messages in a single segment,
        and returns a truncated segment.
     - memory_fn*: Takes a list of segments (ie list of lists),
        and returns a globally truncated memory.
    """

    @staticmethod
    def _is_pinned(msg: str, pinned_messages):
        remove_id = msg.split("]")[-1]
        return pinned_messages is not None and remove_id in pinned_messages

    @staticmethod
    def segment_fn_last_n(segment, pinned_messages=None, n=3):
        """Keep last n messages in each segment."""
        trunc_token = "<TRUNC>"

        if len(segment) <= n:
            return segment

        truncated = []
        for i in range(len(segment)):
            if MemoryTruncationFunctions._is_pinned(segment[i], pinned_messages):
                if i < len(segment) - n - 1:
                    truncated += [segment[i], trunc_token]
                elif i < len(segment) - n:
                    truncated += [segment[i]]

        if len(truncated) == 0 or truncated[-1] != trunc_token:
            truncated = truncated + [trunc_token]

        truncated = truncated + segment[-n:]
        return truncated

    @staticmethod
    def segment_fn_noop(segment, pinned_messages=None):
        """No-op segment truncation."""
        return segment

    @staticmethod
    def memory_fn_noop(segments, pinned_messages=None):
        """No-op memory truncation."""
        return segments

    @staticmethod
    def memory_fn_by_token(segments, pinned_messages=None, max_input_tokens=4096):
        trunc_token = "<TRUNC>"

        max_tokens_per_segment = [max_input_tokens // len(segments)] * len(segments)
        max_tokens_per_segment[-1] += max_input_tokens - sum(max_tokens_per_segment)

        truncated = []

        for i, segment in enumerate(segments):
            cnt = 0

            trunc_segment = [None for _ in range(len(segment))]
            trunc_flag = False

            for j in range(len(segment) - 1, -1, -1):
                tokens = segment[j].split()
                cnt += len(tokens)

                pinned = MemoryTruncationFunctions._is_pinned(
                    segment[j], pinned_messages
                )
                if not pinned and cnt >= max_tokens_per_segment[i]:
                    if not trunc_flag:
                        trunc = " ".join(tokens[cnt - max_tokens_per_segment[i] :])
                        trunc_segment[j] = trunc_token + trunc
                        trunc_flag = True
                    continue

                trunc_segment[j] = segment[j]

            truncated.append([x for x in trunc_segment if x is not None])

        return truncated

    @staticmethod
    def validate_segment_trunc_fn(fn):
        assert type(fn(["msg1", "msg2"])) == list, (
            "Segment truncation_fn should take list of messages and "
            "output truncated list."
        )
        assert "msg1" in fn(
            ["msg1", "msg2"], pinned_messages={"msg1"}
        ), "Segment truncation_fn should respect pin."

    @staticmethod
    def validate_memory_trunc_fn(fn):
        res = fn([["msg1", "msg2"], ["msga", "msgb"]])
        assert (
            type(res) is list and type(res[0]) is list
        ), "Memory truncation_fn should take list of segments and output truncated list"

        res = fn([["msg1", "msg2"], ["msga", "msgb"]], pinned_messages={"msg1"})
        assert "msg1" in [
            y for x in res for y in x
        ], "Memory truncation_fn should respect pin"


@dataclass
class MemoryResourceConfig(BaseResourceConfig):
    """Configuration for MemoryResource"""

    scope: MemoryScope = field(default=MemoryScope.WORKFLOW)
    fmt: str = field(default=MemoryPrompts.DEFAULT_FMT_WORKFLOW)
    collate_fn: Callable[[List], str] = field(
        default=MemoryCollationFunctions.collate_ordered
    )
    segment_trunc_fn: Callable[[List], List] = field(
        default=partial(MemoryTruncationFunctions.segment_fn_last_n, n=6)
    )
    memory_trunc_fn: Callable[[List], List] = field(
        default=MemoryTruncationFunctions.memory_fn_by_token
    )

    def validate(self) -> None:
        """Validate LLMResource configuration"""
        MemoryPrompts.validate_memory_prompt(self.fmt, self.scope)
        MemoryCollationFunctions.validate_collation_fn(self.collate_fn)
        MemoryTruncationFunctions.validate_segment_trunc_fn(self.segment_trunc_fn)
        MemoryTruncationFunctions.validate_memory_trunc_fn(self.memory_trunc_fn)


class MemoryResource(BaseResource):
    """Memory Resource"""

    def __init__(self, resource_id: str, config: MemoryResourceConfig):
        super().__init__(resource_id, config)
        self.scope = self._resource_config.scope

        # example traversal if scope is workflow, and given message is action_message
        #  1) go up to workflow message, then do a pre-order traversal,
        #     stopping at phase_message that contains the action message
        #  2) go up to that phase_message, then do a pre-order traversal,
        #     stopping at agent_message that contains the action message
        #  3) go up to that agent_message, then do a pre-order traversal,
        #     stopping at given action message
        # This way, we can segment memory into prev_phase, prev_agent, and prev_action
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

        self.pinned_messages = set()

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

        def is_initial_prompt(msg_node):
            return isinstance(msg_node, AgentMessage) and msg_node.agent_id == "system"

        def extract_children(msg_node):
            if hasattr(msg_node, "_phase_messages"):
                return msg_node._phase_messages
            elif hasattr(msg_node, "_agent_messages"):
                return msg_node._agent_messages
            elif hasattr(msg_node, "_action_messages"):
                return msg_node._action_messages
            return []

        def extract_id(msg_node):
            if hasattr(msg_node, "_phase_messages"):
                return msg_node.workflow_id
            elif hasattr(msg_node, "_agent_messages"):
                return msg_node.phase_id
            elif hasattr(msg_node, "_action_messages"):
                return msg_node.agent_id

            assert isinstance(msg_node, ActionMessage)

            if msg_node.parent.agent_id == msg_node.resource_id: 
                return msg_node.parent.agent_id
            return msg_node.parent.agent_id + "/" + msg_node.resource_id

        def add_to_segment(msg_node, segment):
            id_ = extract_id(msg_node)
            if not msg_node._message.strip():
                return

            segment.append(f"[{id_}] {msg_node._message.strip()}")

        def go_up(msg_node, dst_cls):
            down_stop = None
            while not isinstance(msg_node, dst_cls):
                down_stop = msg_node
                msg_node = msg_node.parent
            return msg_node, down_stop

        def go_down(msg_node, sys_messages, stop_instance):
            if is_initial_prompt(msg_node):
                sys_messages.add(msg_node._message)
                return []

            children = extract_children(msg_node)

            # pre-order traversal
            segment = []
            if hasattr(msg_node, "_message"):
                # if AgentMessage has action messages, don't add agent._message
                # this is to avoid duplicates, as agent._message will include
                # all action messages otherwise
                if not isinstance(msg_node, AgentMessage) or len(children) == 0:
                    add_to_segment(msg_node, segment)

            if len(children) > 0:
                child = children[0].get_latest_version()
                while child.next:
                    if child is stop_instance:
                        break
                    segment.extend(go_down(child, sys_messages, stop_instance))
                    child = child.next.get_latest_version()

                if child is not stop_instance:
                    segment.extend(go_down(child, sys_messages, stop_instance))

            return segment

        stop_cls = self.stop_cls
        segments = []

        # collect system messages (initial_prompts) separately
        system_messages = set()
        while not isinstance(message, stop_cls):
            root, down_stop = go_up(message, stop_cls)
            segments.append(
                go_down(root, sys_messages=system_messages, stop_instance=down_stop)
            )
            stop_cls = self.message_hierarchy[stop_cls]

        if is_initial_prompt(message):
            system_messages.add(message._message)
        else:
            if hasattr(message, "_message") and message._message:
                add_to_segment(message, segments[-1])

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

    def pin(self, message_str: str):
        """
        Pins message.

        Currently, pin is content-based.
        """
        self.pinned_messages.add(message_str.strip())

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
            "pinned_messages": list(self.pinned_messages),
        }
