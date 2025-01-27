from dataclasses import dataclass, field
from enum import Enum
import string
from typing import Callable, List
from functools import partial
from resources.base_resource import BaseResource, BaseResourceConfig
from messages.agent_messages.agent_message import AgentMessage, ActionMessage
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
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
        "In addition to the above task, you are also provided the transaction history of the system.\n"
        "You should account for previous messages (if present) that have occurred when formulating your response:"
    )

    _DEFAULT_SEGMENTS = (
        " - Current workflow, previous phase messages: {prev_phase_messages}\n"
        " - Current phase, previous agents messages: {prev_agent_messages}\n"
        " - Current agent, previous action messages: {prev_action_messages}"
    )

    DEFAULT_FMT_WORKFLOW = '\n'.join([_DEFAULT_SEGUE, _DEFAULT_SEGMENTS])
    DEFAULT_FMT_PHASE = '\n'.join([_DEFAULT_SEGUE, '\n'.join(_DEFAULT_SEGMENTS.split('\n')[1:])])
    DEFAULT_FMT_AGENT = '\n'.join([_DEFAULT_SEGUE, '\n'.join(_DEFAULT_SEGMENTS.split('\n')[2:])])

    @staticmethod
    def validate_memory_prompt(prompt, scope: MemoryScope): 
        kwargs = ['prev_phase_messages', 'prev_agent_messages', 'prev_action_messages'][scope.value:]
        kwargs = set(kwargs)

        user_keys = set(x[1] for x in string.Formatter().parse(prompt) if x[1] is not None)

        if user_keys != kwargs:
            diffs = (user_keys - kwargs) | (kwargs - user_keys)
            raise ValueError(f"Format string does not match expected input for {str(scope)}\n"
                             f"Expected format string kwargs: {kwargs}\n"
                             f"Inputted format string kwargs: {user_keys}\n"
                             f"Mismatched kwargs: {diffs}")


class MemoryCollationFunctions: 
    """
    Collection of memory collation functions. 
    
    Collation functions should take a list of messages of a single segment, 
    e.g., prev_agent_messages, and convert it into a single string.
    Each memory can have up to three segments, as defined in MemoryPrompts.
    """
    @staticmethod
    def collate_ordered(segment): 
        """Join each message and prepend enumeration."""
        return "\n".join(f"{i+1}) {message}" for i, message in enumerate(segment))
    
    @staticmethod
    def validate_collation_fn(fn):
        assert type(fn(['msg1', 'msg2'])) == str, f"Memory collation_fn should take list of messages and output str."


class MemoryTruncationFunctions:
    """
    Collection of memory truncation functions. 

    There are two types of truncation functions.
     - segment_fn*: Takes a list of messages in a single segment, and returns a truncated segment.
     - memory_fn*: Takes a list of segments (ie list of lists), amd returns a globally truncated memory.
    """
    @staticmethod
    def segment_fn_last_n(segment, pinned_messages=None, n=3): 
        """Keep last n messages in each segment."""
        trunc_token =  "...<TRUNCATED>..."

        if len(segment) <= n: 
            return segment

        truncated = []
        for i in range(len(segment)): 
            if pinned_messages and segment[i] in pinned_messages:
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
    def validate_segment_trunc_fn(fn): 
        assert type(fn(['msg1', 'msg2'])) == list, f"Segment truncation_fn should take list of messages and output truncated list."
        assert 'msg1' in fn(['msg1', 'msg2'], pinned_messages={'msg1'}), "Segment truncation_fn should respect pin."
    
    @staticmethod
    def validate_memory_trunc_fn(fn): 
        res = fn([['msg1', 'msg2'], ['msga', 'msgb']])
        assert type(res) == list and type(res[0]) == list, f"Memory truncation_fn should take list of segments and output truncated list."

        res = fn([['msg1', 'msg2'], ['msga', 'msgb']], pinned_messages={'msg1'})
        assert 'msg1' in [y for x in res for y in x], f"Memory truncation_fn should respect pin"


@dataclass
class MemoryResourceConfig(BaseResourceConfig):
    """Configuration for MemoryResource"""
    scope: MemoryScope = field(default=MemoryScope.WORKFLOW)
    fmt: str = field(default=MemoryPrompts.DEFAULT_FMT_WORKFLOW)
    collate_fn: Callable[[List], str] = field(default=MemoryCollationFunctions.collate_ordered)
    segment_trunc_fn: Callable[[List], List] = field(default=partial(MemoryTruncationFunctions.segment_fn_last_n, n=3))
    memory_trunc_fn: Callable[[List], List] = field(default=MemoryTruncationFunctions.memory_fn_noop)

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
            ActionMessage: ActionMessage
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
        assert isinstance(message, (ActionMessage, AgentMessage, PhaseMessage)), f"Invalid message type {type(message)} passed to memory"

        def is_initial_prompt(msg_node): 
            return isinstance(msg_node, AgentMessage) and msg_node.agent_id == 'system'

        def go_up(msg_node, dst_cls): 
            while not isinstance(msg_node, dst_cls): 
                while msg_node.prev: 
                    msg_node = msg_node.prev
                msg_node = msg_node.parent
            return msg_node
        
        def go_down(msg_node, sys_messages, root_run=False): 
            children = []
            if hasattr(msg_node, '_phase_messages'): 
                children = msg_node._phase_messages
            elif hasattr(msg_node, '_agent_messages'):
                children = msg_node._agent_messages
            elif hasattr(msg_node, '_action_messages'): 
                # exclude any system messages, ie initial prompts
                if is_initial_prompt(msg_node):
                    sys_messages.add(msg_node._message)
                    return []
                children = msg_node._action_messages
            
            if root_run:
                children = children[:-1]
            
            # pre-order traversal
            messages = []
            if hasattr(msg_node, '_message'): 
                messages.append(msg_node._message)

            for child in children: 
                messages.extend(go_down(child, sys_messages))

            return messages

        stop_cls = self.stop_cls

        messages = [] 

        # collect system messages (initial_prompts) separately
        system_messages = set()
        while not isinstance(message, stop_cls): 
            root = go_up(message, stop_cls)
            messages.append(go_down(root, sys_messages=system_messages, root_run=True))
            stop_cls = self.message_hierarchy[stop_cls]

        if is_initial_prompt(message): 
            system_messages.add(message._message)
        else:
            if hasattr(message, '_message') and message._message:
                messages[-1].append(message._message.strip())

        # truncate each segment
        trunc_messages = [self.segment_trunc_fn(x, self.pinned_messages) for x in messages]

        # truncate all memory
        trunc_messages = self.memory_trunc_fn(trunc_messages, self.pinned_messages)

        messages = [list(filter(lambda x: x.strip() != '', msgs)) for msgs in trunc_messages]
        messages = [self.collate_fn(x) for x in messages]

        return messages, system_messages

    def get_memory(self, message: ActionMessage | AgentMessage | PhaseMessage):
        messages, system_messages = self.parse_message(message)

        assert len(system_messages) == 1, \
            (f"Current memory implementation only supports single initial prompt.\n"
             f"Found {len(system_message)} initial prompts (system messages)" +
             f":\n\t{[msg[:25] + '...' for msg in system_messages]}\n" if system_messages else ""
            )
        
        system_message = system_messages.pop()
        
        kwargs = ['prev_phase_messages', 'prev_agent_messages', 'prev_action_messages'][self.scope.value:] 

        assert len(messages) <= len(kwargs) 

        while len(messages) < len(kwargs): 
            messages.append('')
        
        messages = [x if x else 'N/A' for x in messages]
        kwargs = {k: m for k, m in zip(kwargs, messages)}

        memory_str = self.fmt.format(**kwargs)

        memory_str = f"{system_message}\n\n" + memory_str

        return memory_str
        

    def pin(self, message_str: str):
        """
        Pins message. 

        Currently, pin is content-based.
        """
        self.pinned_messages.add(message_str.strip())
        

    def stop(self): 
        logger.debug(f"Stopping Memory resource {self.resource_id} (no cleanup required)")
