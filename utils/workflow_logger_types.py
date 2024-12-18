from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from responses.response import Response

class ActionType(Enum):
    LLM = "llm"


@dataclass
class Action:
    action_type: ActionType
    input_data: Any
    output_data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentInteraction:
    agent_name: str
    input_data: Response
    output_data: Response
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    actions: List[Action] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowIteration:
    iteration_number: int
    interactions: List[AgentInteraction]
    status: str

@dataclass
class WorkflowMetadata:
    workflow_name: str
    start_time: str
    end_time: Optional[str] = None
    task_repo_dir: Optional[str] = None
    bounty_number: Optional[str] = None
    model_config: Optional[Dict[str, Any]] = None
    additional_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowLog:
    metadata: WorkflowMetadata
    iterations: List[WorkflowIteration]
    resources_used: List[str] = field(default_factory=list)
    final_status: str = "in_progress"
    error_log: List[Dict[str, Any]] = field(default_factory=list)
