from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from responses.response import Response

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
    agent_name: str
    input_response: Optional[Response]
    output_response: Optional[Response]
    start_time: str
    end_time: Optional[str]
    actions: List[Action] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
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

@dataclass
class WorkflowMetadata:
    workflow_name: str
    start_time: str
    end_time: Optional[str] = None
    task_repo_dir: Optional[str] = None
    bounty_number: Optional[str] = None
    additional_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowLog:
    metadata: WorkflowMetadata
    phases: List[WorkflowPhase] = field(default_factory=list)
    resources_used: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    agent_used: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    final_status: List[str] = field(default_factory=list)
    error_log: List[Dict[str, Any]] = field(default_factory=list)
