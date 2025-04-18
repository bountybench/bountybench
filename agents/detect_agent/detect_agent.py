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

SETUP_FILES_DIR = "setup_files"
logger = get_main_logger(__name__)


@dataclass
class DetectAgentConfig(AgentConfig):
    bounty_dir: Path
    task_dir: Path
    tmp_dir: Path
    submit: bool
    install_command: Optional[str] = None

    def to_dict(self):
        return {
            "bounty_dir": str(self.bounty_dir),
            "task_dir": str(self.task_dir),
            "tmp_dir": str(self.tmp_dir),
            "submit": self.submit,
            "install_command": self.install_command,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            bounty_dir=Path(data["bounty_dir"]),
            task_dir=Path(data["task_dir"]),
            tmp_dir=Path(data["tmp_dir"]),
            submit=data["submit"],
            install_command=data["install_command"],
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
        self.install_command = agent_config.install_command

        self.exploit_files_dir = self.tmp_dir / "exploit_files"
        self.agent_exploit_script = self.exploit_files_dir / "exploit.sh"

        super().__init__(agent_id, agent_config)

        if not self.exploit_files_dir.exists():
            self.exploit_files_dir.mkdir(parents=True, exist_ok=True)

        self.log_history = []

        git_init_repo(self.tmp_dir, ignore_dirs=["codebase"])
        # TODO: stop bounty_level setup

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

        if self.submit:
            if (
                not isinstance(prev_agent_message, ExecutorAgentMessage)
                or not prev_agent_message.submission
            ):
                combined_log = self._log("Waiting for the submission...", clear=True)
                detect_agent_message.set_message(combined_log)
                return detect_agent_message
            detect_agent_message.set_submission(True)
            self._log("Received submission. Evaluating Agent Exploit...")

        if not self.agent_exploit_script.exists():
            combined_log = self._log("No exploit.sh found.", clear=True)
            detect_agent_message.set_message(combined_log)
            return detect_agent_message

        if not git_has_changes(self.exploit_files_dir, check_all=False):
            combined_log = self._log(
                "No file changes detected in exploit_files.", clear=True
            )
            detect_agent_message.set_message(combined_log)
            return detect_agent_message

        git_commit(self.tmp_dir, subfolder_to_commit=self.exploit_files_dir)

        self.restart_resources()
        exit_code = await self.run_agent_exploit(detect_agent_message)
        if exit_code != 0:
            combined_log = self._log(
                f"Exploit failed with exit code {exit_code}.", clear=True
            )
            detect_agent_message.set_message(combined_log)
        else:
            combined_log = self._log("Agent exploit succeeded.")
            # TODO - add the agent scoring logic
            success = False
            detect_agent_message.set_message(f"{combined_log}")

            if success:
                detect_agent_message.set_success(True)
                return detect_agent_message

        # Since we mount task_dir codebase into tmp_dir/codebase, clean up both paths
        git_clean(self.task_dir)
        git_clean(self.tmp_dir)
        self.restart_resources()
        self.log_history.clear()
        return detect_agent_message

    async def run_agent_exploit(self, detect_agent_message: DetectAgentMessage):
        try:
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
        script_path = self.exploit_files_dir / "run_exploit.sh"
        try:
            install_command = (
                self.install_command
                if self.install_command
                else "pip install --quiet -e ."
            )

            # Create a shell script in the tmp directory that will handle the installation and exploit
            script_content = f"""#!/bin/bash
# Check if Python project and install if needed
if [ -f /app/codebase/setup.py ] || [ -f /app/codebase/pyproject.toml ]; then
# Redirect this output to /dev/null
echo "Python project detected. Installing in editable mode..." > /dev/null
(cd /app/codebase && {install_command} && cd -) > /dev/null 2>&1
else
echo "Not a Python project or setup file not found. Skipping pip install." > /dev/null
fi

# Run the exploit script
bash /app/exploit_files/exploit.sh
"""

            with open(script_path, "w") as f:
                f.write(script_content)

            script_path.chmod(script_path.stat().st_mode | 0o755)
            exploit_command = "bash /app/exploit_files/run_exploit.sh"

            tmp_dir_host_path = str(self.resources.init_files.tmp_dir.resolve())
            task_dir_codebase_path = str((self.task_dir / "codebase").resolve())
            volumes = {
                tmp_dir_host_path: {
                    "bind": "/app",
                    "mode": "rw",
                },
                # Overwrite tmp_dir codebase with task_dir codebase
                task_dir_codebase_path: {
                    "bind": "/app/codebase",
                    "mode": "rw",
                },
            }

            agent_exploit_message = DockerActionMessage(
                resource_id=f"agent_exploit_{self.resources.docker.resource_id}",
                docker_image="cybench/bountyagent:latest",
                command=exploit_command,
                network="shared_net",
                volumes=volumes,
            )

            agent_exploit_message = await self.resources.docker.run(
                agent_exploit_message
            )
            self._log(
                f"Output from agent exploit.sh: \n{agent_exploit_message.message}"
            )

        except Exception as e:
            raise e

        finally:
            # Clean up the temporary script file
            if script_path.exists():
                script_path.unlink()

            return agent_exploit_message

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
