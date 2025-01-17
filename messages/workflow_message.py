from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class WorkflowMessage(Message):
    def __init__(self, workflow_name: str, workflow_id: Optional[str] = None, task: Optional[Dict[str, Any]] = None, logs_dir: str = "logs") -> None:
        
        super().__init__()
        # Core
        self._success = False
        self._complete = False
        self._phase_messages = []
        self.agents_used = {}
        self.resources_used = {}

        # Logging
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)

        components = [workflow_name]
        for _, value in task.items():
            if value:
                components.append(str(value.name if isinstance(value, Path) else value))
        self.log_file = self.logs_dir / f"{'_'.join(components)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.worfklow_id = workflow_id

        # Metadata
        self.workflow_name = workflow_name
        self._start_time = datetime.now().isoformat()
        self._end_time = None
        self._phase_status = {}
    @property
    def success(self) -> bool:
        return self._success
    
    @property
    def complete(self) -> bool:
        return self._complete
    
    @property
    def phase_messages(self) -> List[PhaseMessage]:
        return self._phase_messages

    def set_success(self):
        self._success = True

    def set_complete(self):
        self._complete = True

    def add_phase_message(self, phase_message: PhaseMessage):
        self._phase_messages.append(phase_message)

    def save(self):
        self._end_time = datetime.now().isoformat()
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.log_file, 'w') as f:
            json.dump(self.to_dict(), f, indent=4, default=self._json_serializable)
            logger.status(f"Saved log to: {self.log_file}")

    def add_agent(self, agent_name: str, agent) -> None:
        if agent_name not in self.agents_used and hasattr(agent, 'to_dict'):
            self.agents_used[agent_name] = agent.to_dict()

    def add_resource(self, resource_name: str, resource) -> None:
        if resource_name not in self.resources_used and hasattr(resource, 'to_dict'):
            self.resources_used[resource_name] = resource.to_dict()

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "complete": self.complete,
            "phase_messages": [phase_message.to_dict() for phase_message in self._phase_messages]
        }