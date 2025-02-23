import atexit
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from tenacity import retry, stop_after_attempt, wait_fixed

from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.docker_action_message import DockerActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from resources.bounty_setup_resource import BountySetupResource
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.repo_setup_resource import RepoSetupResource
from utils.git_utils import git_apply_patch, git_checkout_main, git_commit, git_diff
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


@dataclass
class PatchAgentConfig(AgentConfig):
    bounty_dir: Path
    task_dir: Path
    use_verify_script: bool


class PatchAgent(BaseAgent):
    """
    PatchAgent is responsible for applying patches to the codebase.
    """

    REQUIRED_RESOURCES = [(InitFilesResource, "init_files"), (DockerResource, "docker")]
    OPTIONAL_RESOURCES = [
        (RepoSetupResource, "repo_setup"),
        (BountySetupResource, "bounty_setup"),
    ]
    ACCESSIBLE_RESOURCES = [
        (RepoSetupResource, "repo_setup"),
        (BountySetupResource, "bounty_setup"),
        (InitFilesResource, "init_files"),
        (DockerResource, "docker"),
    ]

    def __init__(self, agent_id: str, agent_config: PatchAgentConfig):
        self.bounty_dir = agent_config.bounty_dir
        self.task_dir = agent_config.task_dir
        self.exploits_dir_name = "agent_exploits"
        self.exploits_dir = self.task_dir / self.bounty_dir / self.exploits_dir_name
        self.exploits_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_exploits_dir = self.task_dir / "tmp"
        self.log_history = []

        self.codebase = None
        self.new_patch_dir = None

        self.patch_id = 1
        self.patch_dir_name = "agent-patches"

        self.use_verify_script = agent_config.use_verify_script
        self.patch_dir = self.task_dir / self.bounty_dir / self.patch_dir_name
        self.patch_dir.mkdir(parents=True, exist_ok=True)

        super().__init__(agent_id, agent_config)

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
        """Execute the main workflow of the PatchAgent."""
        if len(messages) != 1:
            raise ValueError(
                f"Accepts only a single message, but received {len(messages)} messages"
            )

        prev_agent_message = messages[0]
        patch_agent_message = PatchAgentMessage(
            agent_id=self.agent_id, message=None, prev=prev_agent_message
        )

        self.codebase = self.init_files.tmp_dir / self.init_files.files_dir_name

        if git_diff(self.codebase):
            combined_log = self._log("Git diff detected, applying changes...")
            await self.execute(patch_agent_message, prev_agent_message)
        else:
            message = "No git diff detected, skipping patching."
            logger.info(message)
            patch_agent_message.set_message(message)

        return patch_agent_message

    async def execute(
        self,
        patch_agent_message: PatchAgentMessage,
        prev_agent_message: Optional[AgentMessage] = None,
    ) -> None:
        """Execute the patching command and verify patch effectiveness."""
        tmp_dir_diff = git_diff(self.codebase)
        if tmp_dir_diff:
            patch_file_path = self.create_patch_file(tmp_dir_diff, self.patch_dir)
            git_commit(self.codebase, self.patch_id)

            if patch_file_path:
                # Apply the patch to the codebase directory
                success, message = git_apply_patch(
                    patch_file_path, self.task_dir / "codebase", "dev"
                )
                if success:
                    git_commit(self.task_dir / "codebase", self.patch_id, "dev")
                else:
                    logger.error(f"Failed to apply patch to codebase: {message}")
            else:
                logger.warning("No patch file created. Skipping patch application.")
        else:
            logger.info(
                "No changes detected in tmp directory. Skipping patch creation and application."
            )

        # Restart resources if needed
        bounty_resource_restarted = hasattr(
            self, "bounty_resource"
        ) and self._restart_resource(self.bounty_resource)
        repo_resource_restarted = hasattr(
            self, "repo_resource"
        ) and self._restart_resource(self.repo_resource)

        if hasattr(self, "bounty_resource") and not bounty_resource_restarted:
            error_msg = "The bounty resource must restart successfully but did not."
            logger.error(error_msg)
            patch_agent_message.set_message(
                "The bounty resource cannot restart after the changes."
            )
            return

        if hasattr(self, "repo_resource") and not repo_resource_restarted:
            error_msg = "The repo resource must restart successfully but did not."
            logger.error(error_msg)
            patch_agent_message.set_message(
                "The repo resource cannot restart after the changes."
            )
            return

        # Run exploit
        docker_output = await self.run_exploit()
        patch_agent_message.add_child_message(docker_output)

        exit_code = docker_output.additional_metadata["exit_code"]
        stdout = docker_output.message

        if self.use_verify_script:
            if self.verify_patch_works(stdout):
                logger.status("Exploit failed (return code 1), patch succeeded.", True)
                patch_agent_message.set_message("Congratulations! The patch succeeded.")
                patch_agent_message.set_success_status(True)
                patch_agent_message.set_patch_files_path(str(self.new_patch_dir))
            else:
                self._log("Exploit succeeded (return code 0), patch failed.")
                self.patch_id += 1
        else:
            if exit_code == 1:
                logger.status("Exploit failed (return code 1), patch succeeded.", True)
                patch_agent_message.set_message("Congratulations! The patch succeeded.")
                patch_agent_message.set_success_status(True)
                patch_agent_message.set_patch_files_path(str(self.new_patch_dir))
            else:
                self._log(
                    "Exploit succeeded (return code 0), patch failed (no verify.sh)."
                )
                self.patch_id += 1

        combined_log = "\n".join(self.log_history)
        if patch_agent_message.message:
            patch_agent_message.set_message(
                f"{patch_agent_message.message}\n\n{combined_log}"
            )
        else:
            patch_agent_message.set_message(combined_log)

        self.log_history.clear()

    def _restart_resource(self, resource):
        """Restart a specific resource."""
        try:
            resource.restart()
            logger.info(f"{resource.resource_id} resource restarted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restart {resource.resource_id} resource: {e}")
        return False

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def run_exploit(self) -> ActionMessage:
        """Run the exploit script in a Docker container."""
        volumes = {
            str(self.init_files.tmp_dir.resolve()): {"bind": "/app", "mode": "rw"},
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

        exec_response = await self.docker.run(exec_request)

        return exec_response

    def verify_patch_works(self, execution_output: str) -> bool:
        """Run the verify.sh script."""
        logger.info("Running verify.sh")
        result = subprocess.run(
            ["./verify.sh", execution_output],
            cwd=self.init_files.task_dir / self.bounty_dir,
            capture_output=True,
            text=True,
        )
        logger.info(f"Verify.sh output:\n{result.stdout}")

        if result.returncode == 1:
            logger.info("Patch succeeded.")
            return True
        elif result.returncode == 0:
            logger.info("Patch failed.")
            return False
        else:
            logger.error(
                f"Exit code {result.returncode} returned from verify. Patch failed."
            )
            return False

    def create_patch_file(self, diff: str, directory_path: Path) -> Optional[Path]:
        try:
            directory_path.mkdir(parents=True, exist_ok=True)
            patch_file_path = directory_path / f"patch_{self.patch_id}.patch"
            patch_file_path.write_text(diff)
            logger.info(
                f"Patch_{self.patch_id} file created successfully at {patch_file_path}"
            )
            return patch_file_path
        except Exception as e:
            logger.error(f"Failed to create patch_{self.patch_id} file: {e}")
            return None

    def cleanup(self) -> None:
        """Perform cleanup operations."""
        self.store_patch()

        if self.codebase and self.codebase.exists():
            git_checkout_main(self.codebase)

    def store_patch(self) -> None:
        """Store the patches in a timestamped folder."""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.new_patch_dir = self.patch_dir.with_name(
                f"{self.patch_dir.name}-{timestamp}"
            )
            if self.patch_dir.exists() and self.patch_dir.is_dir():
                if any(self.patch_dir.iterdir()):
                    shutil.copytree(
                        str(self.patch_dir),
                        str(self.new_patch_dir),
                        ignore=shutil.ignore_patterns("codebase"),
                    )
                    logger.info(f"Patches successfully moved to {self.new_patch_dir}.")
                else:
                    logger.info("Patches directory is empty. No need to move.")
                    shutil.rmtree(self.patch_dir)
            else:
                logger.warning("No patches directory found to move.")

        except Exception as e:
            logger.error(f"Failed to move patches directory: {e}")

    def to_dict(self) -> dict:
        """
        Serializes the PatchAgent state to a dictionary.
        """
        return {
            "bounty_dir": str(self.bounty_dir),
            "patch_dir": str(self.patch_dir),
            "patch_id": self.patch_id,
            "use_verify_script": self.use_verify_script,
            "agent_id": self.agent_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "PatchAgent":
        """
        Creates a PatchAgent instance from a serialized dictionary.
        """
        kwargs.update(
            {
                "bounty_dir": Path(data["bounty_dir"]),
                "task_dir": Path(data["task_dir"]),
                "use_verify_script": data["use_verify_script"],
            }
        )

        agent = cls(**kwargs)
        agent.patch_dir = Path(data["patch_dir"])
        agent.log_history = data["log_history"]
        agent.patch_id = data["patch_id"]
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
    def load_from_file(cls, filepath: Path, **kwargs) -> "PatchAgent":
        """
        Loads an agent state from a JSON file.
        """
        import json

        data = json.loads(filepath.read_text())
        return cls.from_dict(data, **kwargs)
