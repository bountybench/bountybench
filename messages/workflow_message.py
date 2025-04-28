import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from utils.git_utils import git_get_codebase_version
from utils.logger import (
    FULL_LOG_DIR,
    FULL_LOG_FILE_PATH,
    get_main_logger,
    logger_config,
)

logger = get_main_logger(__name__)

# Constants
QUERY_TIME_TAKEN_IN_MS = "query_time_taken_in_ms"
INPUT_TOKEN = "input_token"
OUTPUT_TOKEN = "output_token"


class WorkflowMessage(Message):
    def __init__(
        self,
        workflow_name: str,
        workflow_id: Optional[str] = None,
        task: Optional[Dict[str, Any]] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        logs_dir: str = "logs",
        model_name: Optional[str] = "",
    ) -> None:
        # Core
        self._success = False
        self._complete = False
        self._phase_messages = []
        self.agents_used = {}
        self.resources_used = {}
        self.model_name = model_name
        self.usage = {INPUT_TOKEN: 0, OUTPUT_TOKEN: 0, QUERY_TIME_TAKEN_IN_MS: 0}

        # Metadata
        self.workflow_name = workflow_name
        self.task = task
        self.additional_metadata = additional_metadata
        self._start_time = datetime.now().isoformat()
        self._end_time = None
        self._phase_status = {}
        self._workflow_id = workflow_id if workflow_id else str(id(self))
        from messages.message_utils import message_dict

        message_dict[self.workflow_id] = {}
        message_dict[self.workflow_id][self.workflow_id] = self

        self._codebase_version = git_get_codebase_version()
        self._task_codebase_version = None

        # Logging
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)

        components = []
        if task:
            for _, value in task.items():
                if value:
                    components.append(
                        str(value.name if isinstance(value, Path) else value)
                    )
        self._task_components = "_".join(components)  # e.g. lunary_0

        if task:
            task_dir = task.get("task_dir")
            if task_dir:
                task_dir_root = task_dir.split("/")[0]
                task_codebase = Path(task_dir_root)
                self._task_codebase_version = git_get_codebase_version(task_codebase)

        self.set_full_log_dir_path()
        logger.debug(f"Creating new log file in directory: {self._full_log_dir_path}")

        self.log_file = (
            self._full_log_dir_path
            / f"{self.model_name}_{self.workflow_name}_{self._task_components}_{self.workflow_id}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        )

        super().__init__()

    def _set_parent_from_context(self):
        # WorkflowMessage is the top-level message, so it doesn't have a parent.
        return

    @property
    def success(self) -> bool:
        return self._success

    @property
    def complete(self) -> bool:
        return self._complete

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def phase_messages(self) -> List[PhaseMessage]:
        return self._phase_messages

    @property
    def codebase_version(self) -> str:
        return self._codebase_version

    @property
    def task_codebase_version(self) -> str:
        return self._task_codebase_version

    @property
    def iterations_taken(self) -> int:
        return sum(
            [phase_message.iterations_taken for phase_message in self.phase_messages]
        )

    def set_success(self):
        self._success = True

    def set_complete(self):
        self._complete = True

    def set_full_log_dir_path(self) -> Path:
        self._full_log_dir_path = (
            self.logs_dir
            / Path(datetime.now().strftime("%Y-%m-%d"))
            / Path(self.workflow_name)
            / Path(self._task_components)
            / Path(self.model_name)
        )
        self._full_log_dir_path.mkdir(parents=True, exist_ok=True)

    def get_total_usage(self) -> Dict[str, int]:
        total_input_tokens = sum(
            phase_message.usage[INPUT_TOKEN] for phase_message in self._phase_messages
        )
        total_output_tokens = sum(
            phase_message.usage[OUTPUT_TOKEN] for phase_message in self._phase_messages
        )
        total_time = sum(
            phase_message.usage[QUERY_TIME_TAKEN_IN_MS]
            for phase_message in self._phase_messages
        )
        usage_dict = {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_query_time_taken_in_ms": total_time,
        }
        self.usage = usage_dict
        return usage_dict

    def add_child_message(self, phase_message: PhaseMessage):
        self._phase_messages.append(phase_message)
        phase_message.set_parent(self)
        from messages.message_utils import log_message

        log_message(phase_message)

    def add_agent(self, agent_name: str, agent) -> None:
        if agent_name not in self.agents_used and hasattr(agent, "to_dict"):
            self.agents_used[agent_name] = agent.to_dict()

    def add_resource(self, resource_name: str, resource) -> None:
        if resource_name not in self.resources_used and hasattr(resource, "to_dict"):
            self.resources_used[resource_name] = resource.to_dict()

    def metadata_dict(self) -> dict:
        return {
            "workflow_name": self.workflow_name,
            "workflow_summary": {
                "complete": self.complete,
                "success": self.success,
                "iterations_taken": self.iterations_taken,
            },
            "task": self.task,
        }

    def to_log_dict(self) -> dict:
        return {
            "workflow_metadata": self.metadata_dict(),
            "workflow_usage": self.get_total_usage(),
            "phase_messages": [
                phase_message.to_log_dict() for phase_message in self.phase_messages
            ],
            "agents_used": self.agents_used,
            "resources_used": self.resources_used,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "workflow_id": self.workflow_id,
            "additional_metadata": self.additional_metadata,
            "codebase_version": self.codebase_version,
            "task_codebase_version": self.task_codebase_version,
        }

    def save(self):
        self._end_time = datetime.now().isoformat()
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logs = self.to_log_dict()

        with open(self.log_file, "w") as f:
            json.dump(logs, f, indent=4, default=self._json_serializable)
            logger.status(f"Saved log to: {self.log_file}")

        # Archive the log file
        archive_path = (
            FULL_LOG_DIR
            / self.log_file.parent.relative_to(self.logs_dir)
            / f"{self.log_file.stem}.log"
        )
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Archiving log to: {archive_path}")

        try:
            with open(FULL_LOG_FILE_PATH, "r") as src, open(archive_path, "a") as dst:
                dst.write(src.read())
            FULL_LOG_FILE_PATH.unlink(missing_ok=True)
        except FileNotFoundError:
            logger.warning(
                f"Log file {FULL_LOG_FILE_PATH} not found — skipping archive."
            )

        # Restart logger to attach a fresh FileHandler
        logger_config.restart()

    def on_exit(self):
        # Save the json log file
        self.save()

    def new_log(self):
        components = []
        if self.task:
            for _, value in self.task.items():
                if value:
                    components.append(
                        str(value.name if isinstance(value, Path) else value)
                    )
        self._task_components = "_".join(components)  # e.g. lunary_0

        self.set_full_log_dir_path()
        logger.debug(f"Creating new log file in directory: {self._full_log_dir_path}")

        self.log_file = (
            self._full_log_dir_path
            / f"{self.model_name}_{self.workflow_name}_{self._task_components}_{self.workflow_id}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        )
        logger.status(f"Creating new log file at: {self.log_file}")
        self.save()

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
