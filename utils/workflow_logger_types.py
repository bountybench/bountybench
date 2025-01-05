from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from messages.message import Message

@dataclass
class Action:
    action_type: str
    input_data: Any
    output_data: Any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PhaseIteration:
    iteration_number: int
class PhaseIteration:
    iteration_number: int
    agent_name: str
    input_message: Optional[Message]
    output_message: Optional[Message]
    start_time: str
    end_time: Optional[str]
    end_time: Optional[str]
    actions: List[Action] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "in_progress"
    status: str = "in_progress"

@dataclass
class WorkflowPhase:
    phase_idx: int
    phase_name: str
    start_time: str
    end_time: Optional[str]
    status: str = "in_progress"
    iterations: List[PhaseIteration] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
class WorkflowPhase:
    phase_idx: int
    phase_name: str
    start_time: str
    end_time: Optional[str]
    status: str = "in_progress"
    iterations: List[PhaseIteration] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowMetadata:
    workflow_name: str
    start_time: str
    end_time: Optional[str] = None
    additional_metadata: Dict[str, Any] = field(default_factory=dict)
    task: Optional[Dict[str, Any]] = None

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    task: Optional[Dict[str, Any]] = None

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

@dataclass
class WorkflowLog:
    metadata: WorkflowMetadata
    phases: List[WorkflowPhase] = field(default_factory=list)
    resources_used: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    agents_used: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    final_status: List[str] = field(default_factory=list)
    phases: List[WorkflowPhase] = field(default_factory=list)
    resources_used: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    agents_used: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    final_status: List[str] = field(default_factory=list)
    error_log: List[Dict[str, Any]] = field(default_factory=list)
