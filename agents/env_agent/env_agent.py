import atexit
import time
from dataclasses import dataclass
from pathlib import Path
import re
from queue import Queue
from typing import List, Optional

from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.env_agent_message import EnvAgentMessage
from resources.resource_type import ResourceType
from resources.utils import run_command
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


@dataclass
class EnvAgentConfig(AgentConfig):
    bounty_dir: Path
    task_dir: Path
    tmp_dir: Path


class EnvAgent(BaseAgent):
    """
    EnvAgent is responsible for checking the setup of the environment.
    """

    REQUIRED_RESOURCES = [
        ResourceType.INIT_FILES,
        ResourceType.KALI_ENV,
    ]
    OPTIONAL_RESOURCES = [
    ]
    ACCESSIBLE_RESOURCES = [
        ResourceType.INIT_FILES,
        ResourceType.KALI_ENV,

    ]

    def __init__(self, agent_id: str, agent_config: EnvAgentConfig):
        self.bounty_dir = agent_config.bounty_dir
        self.task_dir = agent_config.task_dir
        self.tmp_dir = agent_config.tmp_dir
        self.container_names = []

        super().__init__(agent_id, agent_config)

        self.log_history = []

        atexit.register(self.cleanup)

    def _log(self, message: str, clear: bool = False) -> str:
        """Helper to append a message to log_history, log it, and return the combined log.
        Optionally clears the history after returning the combined log."""
        self.log_history.append(message)
        logger.info(message)
        combined = "\n".join(self.log_history)
        if clear:
            self.log_history.clear()
        return combined

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        """Execute the main workflow of the ExploitAgent."""
        if len(messages) != 1:
            raise ValueError(
                f"Accepts only a single message, but received {len(messages)} messages"
            )
        self.log_history = []
        prev_agent_message = messages[0]
        env_agent_message = EnvAgentMessage(
            agent_id=self.agent_id, message=None, prev=prev_agent_message
        )

        if "stage1" not in prev_agent_message.message:
            combined_log = self._log("Stage 1 not completed.", clear=True)
            env_agent_message.set_message(f"{combined_log}\nSkipping.")
            return env_agent_message

        await self.execute(env_agent_message, prev_agent_message)
        return env_agent_message

    async def execute(
        self,
        env_agent_message: EnvAgentMessage,
        prev_agent_message: Optional[AgentMessage] = None,
    ) -> None:
        """
        Execute the env setup workflow.
        1. Execute the run_repo_invariants.sh script
        2. Check the container health status
        3. Test if Kali env can connect to the target host
        """
        try:
            script_name = "run_repo_invariants.sh"
            tmp_dir = self.resources.init_files.tmp_dir
            script_path = tmp_dir / script_name
            if not script_path.exists():
                self._log(f"{script_name} not found.", clear=True)
                return
            result = run_command(command=["bash", script_name], work_dir=str(tmp_dir))
            if result.returncode != 0:
                self._log(f"{script_name} failed with return code {result.returncode}", clear=True)
                return
            if (
                result and result.stdout
            ):  # Only process output if result exists and has stdout
                self.container_names = self.extract_container_names(
                    result.stdout, result.stderr
                )
                if self.container_names:
                    success = self.wait_until_all_containers_healthy()
                    if not success:
                        self._log("Failed to wait until all containers healthy.", clear=True)
                        return
        except Exception as e:
            error_msg = f"Error during env setup execution: {str(e)}"
            logger.status(error_msg)
            self.log_history.append(error_msg)
            env_agent_message.set_message("\n".join(self.log_history))

    def wait_until_all_containers_healthy(
        self, timeout: int = 300, check_interval: int = 2
    ) -> bool:
        """
        Wait until all Docker containers are healthy.
        :param timeout: The maximum time in seconds to wait for containers to become healthy.
        :param check_interval: The interval in seconds between health checks.
        :return: True if all containers are healthy before the timeout, otherwise raises TimeoutError.
        """
        if not self.container_names:
            logger.error("No container names available for health check.")
            raise ValueError("No container names available for health check.")

        container_queue = Queue()
        for container in self.container_names:
            container_queue.put(container)

        start_time = time.time()
        try:
            while not container_queue.empty():
                container = container_queue.queue[0]

                inspect_result = run_command(
                    command=[
                        "docker",
                        "inspect",
                        "--format={{json .State.Health.Status}}",
                        container,
                    ]
                )
                health_status = inspect_result.stdout.strip().strip("'\"")

                if health_status == "healthy":
                    logger.info(f"Container '{container}' is healthy.")
                    container_queue.get()
                elif health_status != "starting":
                    raise RuntimeError(
                        f"Container '{container}' has unexpected health status: {health_status}."
                    )

                if time.time() - start_time > timeout:
                    raise TimeoutError(
                        f"Timeout: Not all containers became healthy within {timeout} seconds."
                    )

                time.sleep(check_interval)

            logger.info("All containers are healthy.")
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to wait until all containers healthy: {e}")

    def extract_container_names(
        self, stdout: Optional[str] = None, stderr: Optional[str] = None
    ) -> List[str]:
        """
        Extract the names of all running containers from the setup scripts' output.
        Looks for lines matching the pattern: "Container <name> (Started|Healthy)".
        """
        container_name_pattern = re.compile(r"Container\s+([^\s]+)\s+(Started|Healthy)")

        # Ensure both stdout and stderr are strings
        stdout = stdout.decode("utf-8") if isinstance(stdout, bytes) else (stdout or "")
        stderr = stderr.decode("utf-8") if isinstance(stderr, bytes) else (stderr or "")

        output = stdout + stderr
        matches = container_name_pattern.findall(output)

        if matches:
            container_names = list({match[0] for match in matches})
            logger.info(f"Container names extracted: {container_names}")
            return container_names
        else:
            return []

    def to_dict(self) -> dict:
        """Serializes the EnvAgent state to a dictionary."""
        return {
            "bounty_dir": str(self.bounty_dir),
            "task_dir": str(self.task_dir),
            "tmp_dir": str(self.tmp_dir),
            "agent_id": self.agent_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "EnvAgent":
        """
        Creates an EnvAgent instance from a serialized dictionary.
        """
        kwargs["bounty_dir"] = Path(data["bounty_dir"])
        kwargs["task_dir"] = Path(data["task_dir"])
        kwargs["tmp_dir"] = Path(data["tmp_dir"])
        agent = cls(**kwargs)
        agent.log_history = data["log_history"]
        agent._agent_id = data["agent_id"]
        return agent

    def save_to_file(self, filepath: Path) -> None:
        """
        Saves the agent state to a JSON file.
        """
        import json

        state = self.to_dict()
        filepath.write_text(json.dumps(state, indent=2))

    @classmethod
    def load_from_file(cls, filepath: Path, **kwargs) -> "EnvAgent":
        """
        Loads an agent state from a JSON file.
        """
        import json

        data = json.loads(filepath.read_text())
        return cls.from_dict(data, **kwargs)
