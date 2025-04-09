import atexit
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from tenacity import retry, stop_after_attempt, wait_fixed

from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.docker_action_message import DockerActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.detect_agent_message import DetectAgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from resources.base_resource import ActionMessage
from resources.resource_type import ResourceType
from utils.git_utils import git_clean, git_commit, git_has_changes, git_init_repo
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


@dataclass
class DetectAgentConfig(AgentConfig):
    bounty_dir: Path
    task_dir: Path
    tmp_dir: Path

    submit: bool

    def to_dict(self):
        return {
            "bounty_dir": str(self.bounty_dir),
            "task_dir": str(self.task_dir),
            "submit": self.submit,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            bounty_dir=Path(data["bounty_dir"]),
            task_dir=Path(data["task_dir"]),
        )


class DetectAgent(BaseAgent):
    """
    DetectAgent is responsible for managing and executing detect scripts.

    This agent checks for the presence of a detect.sh file, executes it,
    and verifies its success. It also handles the copying of detect files,
    restarting of resources, and storing of exploit results.
    """

    REQUIRED_RESOURCES = [
        ResourceType.INIT_FILES,
        ResourceType.KALI_ENV,
        ResourceType.DOCKER,
    ]
    OPTIONAL_RESOURCES = [
        ResourceType.BOUNTY_SETUP,
        ResourceType.REPO_SETUP,
    ]
    ACCESSIBLE_RESOURCES = [
        ResourceType.BOUNTY_SETUP,
        ResourceType.REPO_SETUP,
        ResourceType.INIT_FILES,
        ResourceType.DOCKER,
    ]

    def __init__(self, agent_id: str, agent_config: DetectAgentConfig):
        self.bounty_dir = agent_config.bounty_dir
        self.task_dir = agent_config.task_dir
        self.tmp_dir = agent_config.tmp_dir
        self.submit = agent_config.submit

        super().__init__(agent_id, agent_config)

        self.log_history = []

        if not self.submit:
            git_init_repo(self.tmp_dir, ignore_dirs=["codebase"])

        atexit.register(self.cleanup)

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        """Execute the main workflow of the DetectAgent."""
        if len(messages) != 1:
            raise ValueError(
                f"Accepts only a single message, but received {len(messages)} messages"
            )

        prev_agent_message = messages[0]
        detect_agent_message = DetectAgentMessage(
            agent_id=self.agent_id, message=None, prev=prev_agent_message
        )

        exploit_script = self.tmp_dir / "exploit.sh"

        if self.submit:
            if (
                isinstance(prev_agent_message, ExecutorAgentMessage)
                and prev_agent_message.submission
            ):
                self._log("Received submission. Checking for exploit...")
                # Check if exploit script exists
                if not exploit_script.exists():
                    combined_log = self._log("No exploit.sh found.", clear=True)
                    detect_agent_message.set_message(f"{combined_log}\nSkipping.")
                else:
                    exit_code = await self.run_agent_exploit(detect_agent_message)
                    if exit_code != 0:
                        combined_log = self._log(
                            f"Exploit failed with exit code {exit_code}.", clear=True
                        )
                        detect_agent_message.set_message(f"{combined_log}")
                    else:
                        combined_log = self._log(
                            "Exploit succeeded before the validation stage."
                        )
                        await self.execute(detect_agent_message, prev_agent_message)

            else:
                combined_log = self._log("Waiting for the submission...", clear=True)
                detect_agent_message.set_message(f"{combined_log}")
        else:
            if not exploit_script.exists():
                combined_log = self._log("No exploit.sh found.", clear=True)
                detect_agent_message.set_message(f"{combined_log}\n Skipping.")
            else:
                if git_has_changes(self.tmp_dir):
                    git_commit(self.tmp_dir)
                    exit_code = await self.run_agent_exploit(detect_agent_message)
                    if exit_code != 0:
                        combined_log = self._log(
                            f"Exploit failed with exit code {exit_code}.", clear=True
                        )
                        detect_agent_message.set_message(f"{combined_log}")
                    else:
                        combined_log = self._log(
                            "Exploit succeeded before the validation stage."
                        )
                        await self.execute(detect_agent_message, prev_agent_message)
                    git_clean(self.tmp_dir)
                    self.log_history.clear()
                else:
                    combined_log = self._log(
                        "No changes to exploit files detected.", clear=True
                    )
                    detect_agent_message.set_message(f"{combined_log}\nSkipping.")

        return detect_agent_message

    async def run_agent_exploit(self, detect_agent_message: DetectAgentMessage):
        try:
            self.restart_resources()
            logger.info("Executing exploit.sh against the environment.")
            docker_output = await self.run_exploit()
            detect_agent_message.add_child_message(docker_output)
            exit_code = docker_output.additional_metadata["exit_code"]
            exploit_output = docker_output.message
            self._log(f"Execution exploit.sh...\n Output: {exploit_output}.")
        except Exception as e:
            logger.error(f"Failed to execute exploit.sh: {e}")
            self._log(f"Failed to execute exploit.sh: {e}")
            exit_code = 1
        return exit_code

    async def execute(
        self,
        detect_agent_message: DetectAgentMessage,
        prev_agent_message: Optional[AgentMessage] = None,
    ) -> None:
        """Execute the detect workflow."""
        # TODO: Implement the post processing step
        pass

    def cleanup(self) -> None:
        """Perform cleanup operations."""
        try:
            if self.tmp_dir.exists():
                shutil.rmtree(self.tmp_dir)
                logger.info(f"Cleaned up temporary directory: {self.tmp_dir}")
        except Exception as e:
            logger.info(f"Error during final cleanup: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def run_exploit(self) -> ActionMessage:
        """Run the exploit script in a Docker container."""
        volumes = {
            str(self.resources.init_files.tmp_dir.resolve()): {
                "bind": "/app",
                "mode": "rw",
            },
        }

        exploit_command = "bash exploit.sh"

        exec_request = DockerActionMessage(
            resource_id=self.agent_id,
            message="Requesting exploit execution",
            docker_image="cybench/bountyagent:latest",
            command=exploit_command,
            network="shared_net",
            volumes=volumes,
        )

        exec_response = await self.resources.docker.run(exec_request)

        return exec_response

    def restart_resources(self):
        """Restart necessary resources and check success."""
        success = True
        # Must restart repo_setup first, then bounty_setup (same order as initialization)
        if self.resources.has_bound(ResourceType.REPO_SETUP):
            success &= self._restart_resource(self.resources.repo_setup)

        if self.resources.has_bound(ResourceType.BOUNTY_SETUP):
            success &= self._restart_resource(self.resources.bounty_setup)

        if not success:
            logger.error("One or more resources failed to restart.")
        return success

    def _restart_resource(self, resource):
        """Restart a specific resource."""
        try:
            resource.restart()
            logger.info(f"{resource.resource_id} resource restarted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restart {resource.resource_id} resource: {e}")
            return False

    def _log(self, message: str, clear: bool = False) -> str:
        """Helper to append a message to log_history, log it, and return the combined log.
        Optionally clears the history after returning the combined log."""
        self.log_history.append(message)
        logger.info(message)
        combined = "\n".join(self.log_history)
        if clear:
            self.log_history.clear()
        return combined

    def to_dict(self) -> dict:
        """Serializes the DetectAgent state to a dictionary."""
        return {
            "bounty_dir": str(self.bounty_dir),
            "tmp_dir": str(self.tmp_dir),
            "agent_id": self.agent_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    def save_to_file(self, filepath: Path) -> None:
        """
        Saves the agent state to a JSON file.
        """
        import json

        state = self.to_dict()
        filepath.write_text(json.dumps(state, indent=2))

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "DetectAgent":
        """
        Creates an DetectAgent instance from a serialized dictionary.
        """
        kwargs["bounty_dir"] = Path(data["bounty_dir"])
        agent = cls(**kwargs)
        agent.log_history = data["log_history"]
        agent._agent_id = data["agent_id"]
        return agent

    @classmethod
    def load_from_file(cls, filepath: Path, **kwargs) -> "DetectAgent":
        """
        Loads an agent state from a JSON file.
        """
        import json

        data = json.loads(filepath.read_text())
        return cls.from_dict(data, **kwargs)
