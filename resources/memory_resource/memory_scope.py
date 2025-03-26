from enum import Enum


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
