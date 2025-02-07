import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class WorkflowMessage(Message):
    def __init__(
        self,
        workflow_name: str,
        workflow_id: Optional[str] = None,
        task: Optional[Dict[str, Any]] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        logs_dir: str = "logs",
    ) -> None:
        # Core
        self._summary = "incomplete"
        self._phase_messages = []
        self.agents_used = {}
        self.resources_used = {}

        # Logging
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)

        components = [workflow_name]
        if task:
            for _, value in task.items():
                if value:
                    components.append(
                        str(value.name if isinstance(value, Path) else value)
                    )
        self.log_file = (
            self.logs_dir
            / f"{'_'.join(components)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        self._workflow_id = workflow_id if workflow_id else str(id(self))

        # Metadata
        self.workflow_name = workflow_name
        self.task = task
        self.additional_metadata = additional_metadata
        self._start_time = datetime.now().isoformat()
        self._end_time = None
        self._phase_status = {}

        super().__init__()

    @property
    def summary(self) -> str:
        return self._summary

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def phase_messages(self) -> List[PhaseMessage]:
        return self._phase_messages

    def set_summary(self, summary: str):
        self._summary = summary

    def add_phase_message(self, phase_message: PhaseMessage):
        self._phase_messages.append(phase_message)
        phase_message.set_parent(self)

    def add_agent(self, agent_name: str, agent) -> None:
        if agent_name not in self.agents_used and hasattr(agent, "to_dict"):
            self.agents_used[agent_name] = agent.to_dict()

    def add_resource(self, resource_name: str, resource) -> None:
        if resource_name not in self.resources_used and hasattr(resource, "to_dict"):
            self.resources_used[resource_name] = resource.to_dict()

    def metadata_dict(self) -> dict:
        return {
            "workflow_name": self.workflow_name,
            "workflow_summary": self.summary,
            "task": self.task,
        }

    def to_dict(self) -> dict:
        return {
            "workflow_metadata": self.metadata_dict(),
            "phase_messages": [
                phase_message.to_dict() for phase_message in self.phase_messages
            ],
            "agents_used": self.agents_used,
            "resources_used": self.resources_used,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "workflow_id": self.workflow_id,
            "additional_metadata": self.additional_metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowMessage":
        workflow_message = cls(
            workflow_name=data["workflow_metadata"]["workflow_name"],
            workflow_id=data.get("workflow_id"),
            task=data["workflow_metadata"].get("task"),
            additional_metadata=data.get("additional_metadata"),
        )
        workflow_message._summary = data["workflow_metadata"]["workflow_summary"]
        workflow_message._start_time = data.get("start_time")
        workflow_message._end_time = data.get("end_time")
        workflow_message.agents_used = data.get("agents_used", {})
        workflow_message.resources_used = data.get("resources_used", {})

        for phase_data in data.get("phase_messages", []):
            from messages.message_utils import message_from_dict
            phase_message = message_from_dict(phase_data)
            workflow_message.add_phase_message(phase_message)
            
        return workflow_message

    def save(self):
        self._end_time = datetime.now().isoformat()
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logs = self.to_dict()
        for phase_message in logs["phase_messages"]:
            for agent_message in phase_message["agent_messages"]:
                agent_message.pop("current_children", None)
            phase_message.pop("current_children", None)

        with open(self.log_file, "w") as f:
            json.dump(logs, f, indent=4, default=self._json_serializable)
            logger.status(f"Saved log to: {self.log_file}")

    def _json_serializable(self, obj: Any) -> Any:
        if isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, "__dict__"):
            # For objects with a __dict__ attribute (like Message),
            # we'll convert them to a dictionary
            return {
                key: self._json_serializable(value)
                for key, value in obj.__dict__.items()
            }
        elif isinstance(obj, (list, tuple)):
            return [self._json_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._json_serializable(value) for key, value in obj.items()}
        elif hasattr(obj, "__str__"):
            # For any other objects, we'll use their string representation
            return str(obj)
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )
