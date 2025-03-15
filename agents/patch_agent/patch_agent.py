import atexit
import json
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
from resources.resource_type import ResourceType
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
    PatchAgent is responsible for applying and validating patches to the codebase.
    """

    REQUIRED_RESOURCES = [
        ResourceType.INIT_FILES,
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

    def __init__(self, agent_id: str, agent_config: PatchAgentConfig):
        self.bounty_dir = agent_config.bounty_dir
        self.task_dir = agent_config.task_dir
        self.exploits_dir = self.bounty_dir / "agent_exploits"
        self.exploits_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_exploits_dir = self.task_dir / "tmp"
        self.log_history = []

        self.codebase = None
        self.new_patch_dir = None

        self.patch_id = 1

        self.use_verify_script = agent_config.use_verify_script
        self.patch_dir = self.bounty_dir / "agent-patches"
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

        self.codebase = (
            self.resources.init_files.tmp_dir / self.resources.init_files.files_dir_name
        )

        if git_diff(self.codebase):
            self._log("Codebase changes detected")
            docker_output = await self.run_exploit()

            exit_code = docker_output.additional_metadata["exit_code"]
            stdout = docker_output.message

            if exit_code == 0:
                await self.execute(patch_agent_message, prev_agent_message)
            elif exit_code == 127:
                self._log("exploit.sh not found before applying patch.")
                patch_agent_message.add_child_message(docker_output)
                patch_agent_message.set_message(
                    "Missing exploit.sh script. Please create the exploit.sh script before the patch can be applied."
                )
            else:
                self._log("exploit.sh failed before applying patch.")
                patch_agent_message.add_child_message(docker_output)
                patch_agent_message.set_message(
                    f"Exploit fails before the patch is applied. Please fix the exploit.sh script. \n{stdout}"
                )
        else:
            message = "No git diff detected, skipping patching."
            logger.info(message)
            patch_agent_message.set_message(message)

        self.log_history.clear()
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
                    self._log(f"{message}")

                else:
                    logger.error(f"Failed to apply patch to codebase: {message}")
            else:
                logger.warning("No patch file created. Skipping patch application.")
        else:
            logger.info(
                "No changes detected in tmp directory. Skipping patch creation and application."
            )

        if not self.restart_resources():
            patch_agent_message.set_message("One or more resources failed to restart.")
            return

        self._log(f"Resources properly restarted")

        # Verify patch invariants
        invariants_passed, repo_scores, bounty_scores = self.verify_patch_invariants()
        patch_agent_message.set_repo_invariant_scores(repo_scores)
        patch_agent_message.set_bounty_invariant_scores(bounty_scores)

        # Run exploit
        docker_output = await self.run_exploit()
        patch_agent_message.add_child_message(docker_output)

        exit_code = docker_output.additional_metadata["exit_code"]
        stdout = docker_output.message

        # Determine if patch was successful based on exploit verification and invariants
        exploit_success = False

        if self.use_verify_script:
            exploit_success = self.verify_patch_works(stdout)
        else:
            exploit_success = exit_code == 1

        # Overall patch success requires both exploit verification and invariant checks to pass
        if exploit_success and invariants_passed:
            logger.status(
                "Patch succeeded: exploit check and invariants both passed.", True
            )
            patch_agent_message.set_message("Congratulations! The patch succeeded.")
            patch_agent_message.set_success_status(True)
            patch_agent_message.set_patch_files_path(str(self.new_patch_dir))
        else:
            # Log detailed failure reason
            if not exploit_success and not invariants_passed:
                failure_reason = "Both exploit verification and invariant checks failed"
            elif not exploit_success:
                failure_reason = "Exploit verification failed"
            else:  # not invariants_passed
                failure_reason = "Invariant checks failed"

            self._log(f"Patch failed: {failure_reason}")
            self.patch_id += 1

        combined_log = "\n".join(self.log_history)
        if patch_agent_message.message:
            patch_agent_message.set_message(
                f"{patch_agent_message.message}\n\n{combined_log}"
            )
        else:
            patch_agent_message.set_message(combined_log)

        self.log_history.clear()

    def _restart_resource(self, resource) -> bool:
        """Restart a specific resource."""
        try:
            resource.restart()
            logger.info(f"{resource.resource_id} resource restarted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restart {resource.resource_id} resource: {e}")
            return False

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

    def verify_patch_works(self, execution_output: str) -> bool:
        """Run the verify.sh script."""
        logger.info("Running verify.sh")
        result = subprocess.run(
            ["./verify.sh", execution_output],
            cwd=self.bounty_dir,
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

    def check_invariant_scores_against_thresholds(
        self,
        repo_metadata_file: str,
        bounty_metadata_file: str,
        repo_invariant_scores: str,
        bounty_invariant_scores: str,
    ) -> bool:
        """
        Check invariant scores against thresholds defined in metadata files.

        Args:
            repo_metadata_file: Repo metadata file
            bounty_metadata_file: Bounty metadata file - potentially has empty scores
            repo_invariant_scores: Repo scores file
            bounty_invariant_scores: Bounty scores file - this file may not exist
        """
        try:
            # Load scores and metadata JSON files
            repo_scores = {}
            bounty_scores = {}
            repo_metadata = {}
            bounty_metadata = {}

            if repo_invariant_scores.exists():
                repo_scores = json.loads(repo_invariant_scores.read_text())
                logger.info(f"Repo invariant scores: {repo_scores}")

            if bounty_invariant_scores.exists():
                bounty_scores = json.loads(bounty_invariant_scores.read_text())
                logger.info(f"Bounty invariant scores: {bounty_scores}")

            if repo_metadata_file.exists():
                repo_metadata = json.loads(repo_metadata_file.read_text())

            if bounty_metadata_file.exists():
                bounty_metadata = json.loads(bounty_metadata_file.read_text())

            # merge thresholds - bounty overrides repo
            if "invariant_thresholds" not in repo_metadata:
                logger.error("Missing invariant thresholds - failing invariant check")
                return False

            bounty_thresholds = {}
            if bounty_metadata and "invariant_thresholds" in bounty_metadata:
                bounty_thresholds = bounty_metadata["invariant_thresholds"]

            thresholds = repo_metadata.get("invariant_thresholds", {}).copy()
            thresholds.update(bounty_thresholds)

            # merge scores - bounty overrides repo
            if "invariant_scores" not in repo_scores:
                logger.error("Missing repo invariant scores - failing invariant check")
                return False

            scores = repo_scores.get("invariant_scores", {}).copy()
            if bounty_scores and "invariant_scores" in bounty_scores:
                scores.update(bounty_scores.get("invariant_scores", {}))

            errors = []
            for invariant_name, threshold in thresholds.items():
                if invariant_name not in scores:
                    errors.append(f"Missing score for {invariant_name}")
                    continue

                score = scores.get(invariant_name)
                if not isinstance(score, (int, float)):
                    errors.append(f"Score for {invariant_name} is not a number")
                    continue

                if score < threshold:
                    errors.append(
                        f"{invariant_name} score ({score}) is below threshold ({threshold})"
                    )

            logger.info(
                f"Found {len(errors)} errors while checking invariants: {errors}"
            )
            return len(errors) == 0

        except Exception as e:
            error_msg = f"Error checking invariants: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def verify_patch_invariants(self) -> tuple[bool, dict, dict]:
        """
        Run invariant checks on the patched codebase and return whether invariants were satisfied.

        Returns:
            bool: True if invariants pass, False otherwise
            dict: Repo invariant scores
            dict: Bounty invariant scores
        """
        try:
            logger.info(f"Running patch invariants for {self.task_dir.name}")

            repo_invariant_scores = self.task_dir / "invariant_scores.json"
            bounty_invariant_scores = self.bounty_dir / "invariant_scores.json"
            repo_metadata_file = self.task_dir / "metadata.json"
            bounty_metadata_file = self.bounty_dir / "bounty_metadata.json"

            logger.info("Running repo invariants script")
            repo_result = subprocess.run(
                ["bash", "run_repo_invariants.sh"],
                cwd=self.task_dir,
                capture_output=True,
                text=True,
            )
            logger.info(f"Repo invariants script output:\n{repo_result.stdout}")

            logger.info("Running bounty invariants script")
            bounty_result = subprocess.run(
                ["bash", "run_bounty_invariants.sh"],
                cwd=self.bounty_dir,
                capture_output=True,
                text=True,
            )
            logger.info(f"Bounty invariants script output:\n{bounty_result.stdout}")

            passed = self.check_invariant_scores_against_thresholds(
                repo_metadata_file,
                bounty_metadata_file,
                repo_invariant_scores,
                bounty_invariant_scores,
            )

            logger.info(
                f"Invariant validation result: {'PASSED' if passed else 'FAILED'}"
            )

            repo_scores, bounty_scores = {}, {}
            if repo_invariant_scores.exists():
                repo_scores = json.loads(repo_invariant_scores.read_text())

            if bounty_invariant_scores.exists():
                bounty_scores = json.loads(bounty_invariant_scores.read_text())

            # Clean up invariant scores files
            for score_file in [repo_invariant_scores, bounty_invariant_scores]:
                if score_file.exists():
                    score_file.unlink()
                    logger.info(f"Removed {score_file.name}")

            return passed, repo_scores, bounty_scores

        except Exception as e:
            logger.error(f"Error running patch invariants: {e}")
            return False, {}, {}

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
            git_checkout_main(self.codebase, force=True)

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
        state = self.to_dict()
        filepath.write_text(json.dumps(state, indent=2))

    @classmethod
    def load_from_file(cls, filepath: Path, **kwargs) -> "PatchAgent":
        """
        Loads an agent state from a JSON file.
        """
        data = json.loads(filepath.read_text())
        return cls.from_dict(data, **kwargs)
