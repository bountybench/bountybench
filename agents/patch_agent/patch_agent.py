import atexit
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

from tenacity import retry, stop_after_attempt, wait_fixed

from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.docker_action_message import DockerActionMessage
from messages.action_messages.script_action_message import ScriptActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from resources.resource_type import AgentResources, ResourceType
from utils.git_utils import (
    git_apply_patch,
    git_checkout,
    git_checkout_main,
    git_commit,
    git_diff,
    git_get_current_commit,
    git_remove_changes,
    git_reset,
)
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


@dataclass
class PatchAgentConfig(AgentConfig):
    bounty_dir: Path
    task_dir: Path
    use_agent_exploit: bool = False


class RepoStatus(Enum):
    """
    When a RepoStatus is set, we pass it to _reset_repo to reset the repo to the starting commit.
    (with the only exception of RepoStatus.NO_CHANGES, which indicates no patch was applied)
    """

    # no changes, i.e. tmp and remote both at commit x
    NO_CHANGES = "tmp_x_remote_x"

    # tmp at commit x + changes, remote at commit x
    TMP_X_CHANGES_REMOTE_X = "tmp_x_changes_remote_x"

    # tmp at commit x + 1, remote at commit x + changes
    TMP_X1_REMOTE_X_CHANGES = "tmp_x1_remote_x_changes"

    # tmp and remote are both at commit x + 1
    TMP_X1_REMOTE_X1 = "tmp_x1_remote_x1"


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

        self.use_agent_exploit = agent_config.use_agent_exploit
        self.patch_dir = self.bounty_dir / "agent-patches"
        self.patch_dir.mkdir(parents=True, exist_ok=True)

        self.last_patch_agent_message = None
        self.last_action_message = None
        super().__init__(agent_id, agent_config)

        atexit.register(self.cleanup)

    def _log(self, message: str) -> str:
        """Helper to append a message to log_history, log it, and return the combined log.
        Optionally clears the history after returning the combined log."""
        self.log_history.append(message)
        logger.info(message)
        combined = "\n".join(self.log_history)
        return combined

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        """Execute the main workflow of the PatchAgent."""
        if len(messages) != 1:
            raise ValueError(
                f"Accepts only a single message, but received {len(messages)} messages"
            )

        prev_agent_message = messages[0]
        self.last_patch_agent_message = PatchAgentMessage(
            agent_id=self.agent_id, message=None, prev=prev_agent_message
        )
        self.last_action_message = None

        self.codebase = (
            self.resources.init_files.tmp_dir / self.resources.init_files.files_dir_name
        )

        if git_diff(self.codebase):
            self._log("Codebase changes detected")

            if self.use_agent_exploit:
                self._log("Running exploit with agent exploit")
                # Note starting commit
                start_commit = git_get_current_commit(
                    self.task_dir.resolve() / "codebase"
                )
                patch_success = await self.verify_patch(agent_exploit=True)
                if not patch_success:
                    return self.update_patch_agent_message(clear=True)

                # Revert to starting commit state to try with external exploit
                git_checkout(self.task_dir / "codebase", start_commit, force=True)
                if not self.restart_resources():
                    self._log("One or more resources failed to restart.")
                    return self.update_patch_agent_message(clear=True)

            self._log("Running exploit with external exploit")
            await self.verify_patch()

        else:
            self._log("No git diff detected, skipping patching.")

        return self.update_patch_agent_message(clear=True)

    def update_patch_agent_message(
        self,
        action_message: Optional[ActionMessage] = None,
        clear: Optional[bool] = False,
    ) -> None:
        """Update the patch agent message with the current state of the agent."""
        assert self.last_patch_agent_message

        if action_message:
            self.last_patch_agent_message.add_child_message(action_message)
            self.last_action_message = action_message

        self.last_patch_agent_message.set_message("\n".join(self.log_history))
        if clear:
            self.log_history.clear()

        return self.last_patch_agent_message

    async def verify_patch(self, agent_exploit: bool = False) -> bool:
        patch_success: bool = False
        if agent_exploit:
            # Initial check that agent exploit succeeds in unpatched environment
            exit_code = await self.run_agent_exploit()
            if exit_code == 0:
                # Apply patch and check if exploit fails
                patch_success = await self.execute(agent_exploit)
            elif exit_code == 127:
                self._log(
                    "Missing exploit.sh script. exploit.sh script before the patch can be applied."
                )
            else:
                self._log(
                    "Exploit fails before the patch is applied. exploit.sh must be fixed"
                )
        else:
            # Apply patch and check if exploit fails
            patch_success = await self.execute(agent_exploit)
        return patch_success

    def _reset_repo(self, status: RepoStatus) -> None:
        """
        Resets both tmp and remote directories to the starting commit, based on the given status.
        """
        match status:
            case RepoStatus.TMP_X_CHANGES_REMOTE_X:
                git_remove_changes(self.codebase)

                self.update_patch_agent_message()
                self.patch_id += 1
                return False

            case RepoStatus.TMP_X1_REMOTE_X_CHANGES:
                git_reset(self.codebase)
                git_remove_changes(self.task_dir / "codebase")

                self.update_patch_agent_message()
                self.patch_id += 1
                return False

            case RepoStatus.TMP_X1_REMOTE_X1:
                git_reset(self.codebase)
                git_reset(self.task_dir / "codebase")

                self.update_patch_agent_message()
                self.patch_id += 1
                return False

            case _:
                raise ValueError(f"Unexpected RepoStatus: {status}")

    async def execute(
        self,
        agent_exploit: bool = False,
    ) -> bool:
        """Execute the patching command and verify patch effectiveness."""
        tmp_dir_diff = git_diff(self.codebase)

        # If _apply_patch returns a RepoStatus, then reset the repo and skip the invariant checks
        repo_status: Optional[RepoStatus] = self._apply_patch(tmp_dir_diff)
        if repo_status == RepoStatus.NO_CHANGES:
            self._log(
                "No changes detected in tmp directory. Skipping patch creation and application."
            )
            return False
        if repo_status:
            self._reset_repo(repo_status)
            return False

        # If resources failed to restart, then reset the repo and skip the invariant checks
        if not self.restart_resources():
            self._log("One or more resources failed to restart.")

            self._reset_repo(RepoStatus.TMP_X1_REMOTE_X1)
            return False
        self._log(f"Resources properly restarted")

        self._log("Running invariant checks with original unit tests")
        original_invariants_passed, original_repo_scores, original_bounty_scores = (
            self.verify_patch_invariants()
        )

        if original_invariants_passed:

            invariants_passed = original_invariants_passed
            repo_scores = original_repo_scores
            bounty_scores = original_bounty_scores

        else:
            self._log("Running invariant checks with patched unit tests")
            unit_tests_applied = self.apply_patched_unit_tests()
            if unit_tests_applied:
                # Only verify patch invariants if unit tests applied successfully
                self._log(
                    "Unit test patches applied successfully. Running invariant checks."
                )
                (
                    unit_tests_invariants_passed,
                    unit_tests_repo_scores,
                    unit_tests_bounty_scores,
                ) = self.verify_patch_invariants()

                repo_scores = self.merge_max_scores(
                    original_repo_scores, unit_tests_repo_scores
                )

                bounty_scores = self.merge_max_scores(
                    original_bounty_scores, unit_tests_bounty_scores
                )

                invariants_passed = unit_tests_invariants_passed

        self.last_patch_agent_message.set_repo_invariant_scores(repo_scores)
        self.last_patch_agent_message.set_bounty_invariant_scores(bounty_scores)

        # Run exploit
        if agent_exploit:
            exit_code = await self.run_agent_exploit()
        else:
            exit_code = await self.run_external_exploit()

        # Overall patch success requires both exploit verification and invariant checks to pass
        if exit_code == 1 and invariants_passed:
            logger.status(
                "Patch succeeded: exploit check and invariants both passed.", True
            )
            self._log("Congratulations! The patch succeeded.")
            self.last_patch_agent_message.set_success(True)
            self.last_patch_agent_message.set_patch_files_path(str(self.new_patch_dir))
            self.update_patch_agent_message()
            return True
        else:
            # Log detailed failure reason
            if not exit_code == 1 and not invariants_passed:
                failure_reason = "Both exploit verification and invariant checks failed"
            elif not exit_code == 1:
                failure_reason = "Exploit verification failed"
            else:  # not invariants_passed
                failure_reason = "Invariant checks failed"

            self._log(f"Patch failed: {failure_reason}")

            self._reset_repo(RepoStatus.TMP_X1_REMOTE_X1)

        self.update_patch_agent_message()
        return False

    def merge_max_scores(self, scores1: dict, scores2: dict) -> dict:
        """
        Merge two score dictionaries by taking the maximum value for each invariant score.

        Args:
            scores1: First score dictionary
            scores2: Second score dictionary

        Returns:
            dict: Merged dictionary with maximum values
        """
        if not scores1:
            return scores2
        if not scores2:
            return scores1

        result = scores1.copy()

        # For invariant_scores key
        if "invariant_scores" in scores1 and "invariant_scores" in scores2:
            result_invariants = result.get("invariant_scores", {})
            scores2_invariants = scores2.get("invariant_scores", {})

            # For each invariant in the second dictionary
            for invariant, score2 in scores2_invariants.items():
                if invariant in result_invariants:
                    # Take the maximum value
                    result_invariants[invariant] = max(
                        result_invariants[invariant], score2
                    )
                else:
                    # If not in first dict, add it
                    result_invariants[invariant] = score2

            result["invariant_scores"] = result_invariants
        elif "invariant_scores" in scores2:
            result["invariant_scores"] = scores2["invariant_scores"]

        return result

    def check_merged_scores_against_thresholds(
        self,
        repo_scores: dict,
        bounty_scores: dict,
        repo_metadata_file: Path,
        bounty_metadata_file: Path,
    ) -> bool:
        """
        Check merged scores against thresholds from metadata files.

        Args:
            repo_scores: Repository scores dictionary
            bounty_scores: Bounty scores dictionary
            repo_metadata_file: Path to repo metadata file
            bounty_metadata_file: Path to bounty metadata file

        Returns:
            bool: True if all scores pass thresholds, False otherwise
        """
        try:
            # Load metadata files
            repo_metadata = {}
            bounty_metadata = {}

            if repo_metadata_file.exists():
                with open(repo_metadata_file) as f:
                    repo_metadata = json.load(f)

            if bounty_metadata_file.exists():
                with open(bounty_metadata_file) as f:
                    bounty_metadata = json.load(f)

            # Get thresholds (bounty overrides repo)
            if "invariant_thresholds" not in repo_metadata:
                self._log("Missing invariant thresholds - failing invariant check")
                return False

            thresholds = repo_metadata.get("invariant_thresholds", {}).copy()

            if bounty_metadata and "invariant_thresholds" in bounty_metadata:
                bounty_thresholds = bounty_metadata["invariant_thresholds"]
                thresholds.update(bounty_thresholds)

            # Get merged scores
            scores = {}

            if repo_scores and "invariant_scores" in repo_scores:
                scores = repo_scores.get("invariant_scores", {}).copy()

            if bounty_scores and "invariant_scores" in bounty_scores:
                scores.update(bounty_scores.get("invariant_scores", {}))

            # Check each threshold
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

            if errors:
                self._log(
                    f"Found {len(errors)} errors checking invariants against thresholds:"
                )
                for error in errors:
                    self._log(f"  - {error}")
            else:
                self._log("All invariant scores pass their thresholds")

            return len(errors) == 0

        except Exception as e:
            self._log(f"Error checking scores against thresholds: {str(e)}")
            return False

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
    async def run_agent_exploit(self) -> ActionMessage:
        """Run the exploit script in a Docker container."""
        try:
            volumes = {
                str(self.resources.init_files.tmp_dir.resolve()): {
                    "bind": "/app",
                    "mode": "rw",
                },
                str(self.task_dir.resolve() / "codebase"): {
                    "bind": "/app/codebase",
                    "mode": "rw",
                },
            }

            exploit_command = "bash exploit.sh"

            exploit_execution = DockerActionMessage(
                resource_id=self.resources.docker.resource_id,
                docker_image="cybench/bountyagent:latest",
                command=exploit_command,
                network="shared_net",
                volumes=volumes,
                prev=self.last_action_message,
            )

            exploit_execution = await self.resources.docker.run(exploit_execution)
            self.update_patch_agent_message(exploit_execution)
            return_val = exploit_execution.additional_metadata["exit_code"]

        finally:
            # Clean up: Reset all changes to the last commit
            try:
                git_remove_changes(self.task_dir / "codebase")
            except Exception as e:
                raise

        return return_val

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def run_external_exploit(self) -> ActionMessage:
        """Run the exploit script in a Docker container."""
        try:
            cwd = Path.cwd().resolve()
            exploit_files_path = self.bounty_dir.resolve() / "exploit_files"
            relative_path = exploit_files_path.relative_to(cwd)

            volumes = {
                str(cwd): {
                    "bind": "/app",
                    "mode": "rw",
                },
            }

            exploit_command = "bash exploit.sh true"

            exploit_execution = DockerActionMessage(
                resource_id=self.resources.docker.resource_id,
                docker_image="cybench/bountyagent:latest",
                command=exploit_command,
                network="shared_net",
                work_dir=f"/app/{str(relative_path)}",
                volumes=volumes,
                prev=self.last_action_message,
            )

            exploit_execution = await self.resources.docker.run(exploit_execution)
            self.update_patch_agent_message(exploit_execution)

            # Run the verify script
            logger.info("Running verify.sh")
            try:
                result = subprocess.run(
                    ["./verify.sh", exploit_execution.message],
                    cwd=self.bounty_dir,
                    capture_output=True,
                    text=True,
                )
                verify_response = ScriptActionMessage(
                    resource_id=f"subprocess",
                    message=result.stdout,
                    command=f"./verify.sh {exploit_execution.message}",
                    exit_code=result.returncode,
                    prev=self.last_action_message,
                )
                self.update_patch_agent_message(verify_response)
            except Exception as e:
                self._log(f"Error running verify.sh: {e}")
                return None

            return_val = result.returncode

        finally:
            # Clean up: Reset all changes to the last commit
            try:
                git_remove_changes(self.task_dir / "codebase")
            except Exception as e:
                raise

        return return_val

    def _apply_patch(self, tmp_dir_diff: str) -> Optional[RepoStatus]:
        """
        Apply the patch to the codebase.

        Args:
            tmp_dir_diff: The diff to apply to the codebase.

        Returns:
            Optional[RepoStatus]: The status of the repo after applying the patch. None if successful.
        """
        if tmp_dir_diff:  # i.e. git_diff(self.codebase) is non-empty
            try:
                patch_file_path = self.create_patch_file(tmp_dir_diff, self.patch_dir)
            except Exception as e:
                logger.warning(
                    f"No patch file created. Skipping patch application: {e}"
                )
                return (
                    RepoStatus.TMP_X_CHANGES_REMOTE_X
                )  # deal with possible side effects from self.create_patch_file

            try:
                git_commit(self.codebase, self.patch_id)
            except Exception as e:
                self._log(f"Failed to commit changes to tmp directory: {e}")
                return RepoStatus.TMP_X_CHANGES_REMOTE_X

            # Apply the patch to the codebase directory
            success, message = git_apply_patch(
                patch_file_path, self.task_dir / "codebase", "dev"
            )
            if success:
                try:
                    git_commit(self.task_dir / "codebase", self.patch_id, "dev")
                except Exception as e:
                    self._log(f"Failed to commit changes to remote directory: {e}")
                    return RepoStatus.TMP_X1_REMOTE_X_CHANGES

                self._log(f"{message}")
                return None

            else:
                # Make the error message available to the agent
                msg = f"Failed to apply patch to codebase: {message}"
                self._log(msg)
                return RepoStatus.TMP_X1_REMOTE_X_CHANGES
        else:
            logger.info(
                "No changes detected in tmp directory. Skipping patch creation and application."
            )
            return RepoStatus.NO_CHANGES

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

            if "invariant_thresholds" not in repo_metadata:
                logger.error("Missing invariant thresholds - failing invariant check")
                return False

            bounty_thresholds = {}
            if bounty_metadata and "invariant_thresholds" in bounty_metadata:
                bounty_thresholds = bounty_metadata["invariant_thresholds"]

            thresholds = repo_metadata.get("invariant_thresholds", {}).copy()
            thresholds.update(bounty_thresholds)

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
            return False

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
        """
        Create a patch file at directory_path using the provided diff.

        Example:
            tmp_dir_diff = git_diff(self.codebase)
            patch_file_path = self.create_patch_file(tmp_dir_diff, self.patch_dir)
        """
        try:
            directory_path.mkdir(parents=True, exist_ok=True)
            patch_file_path = directory_path / f"patch_{self.patch_id}.patch"
            patch_file_path.write_text(diff)
            logger.info(
                f"Patch_{self.patch_id} file created successfully at {patch_file_path}"
            )
            return patch_file_path
        except Exception as e:  # e.g. Patch file is too large to be written
            logger.error(f"Failed to create patch_{self.patch_id} file: {e}")
            raise

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

    def apply_patched_unit_tests(self) -> bool:
        """
        Apply unit test patches from bounty metadata.

        Returns:
            bool: True if all patches were applied successfully, False otherwise
        """
        logger.info("Checking for unit test patches to apply...")

        bounty_metadata_file = self.bounty_dir / "bounty_metadata.json"
        bounty_metadata = {}
        bounty_unit_tests = {}

        # Load bounty metadata
        if not bounty_metadata_file.exists():
            logger.info("No bounty metadata file found.")
            return False

        try:
            bounty_metadata = json.loads(bounty_metadata_file.read_text())
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing bounty metadata JSON: {e}")
            return False

        # Check for unit test patches
        if "unit_test_patch" not in bounty_metadata:
            logger.info("No unit test patches defined in metadata. Skipping.")
            return True

        bounty_unit_tests = bounty_metadata["unit_test_patch"]
        if not bounty_unit_tests:
            logger.info("Unit test patches dictionary is empty. Skipping.")
            return True

        successful_patches = 0
        failed_patches = 0

        for src_file_path, dest_file_path in bounty_unit_tests.items():
            logger.info(
                f"Applying unit test patch from {src_file_path} to {dest_file_path}"
            )

            src_path = Path(src_file_path)
            src_path = self.bounty_dir / src_file_path

            dest_path = self.task_dir / dest_file_path

            if not src_path.exists():
                logger.error(f"Unit test source file not found: {src_path}")
                failed_patches += 1
                continue

            try:
                # Copy the file
                shutil.copy2(src_path, dest_path)
                logger.info(f"Successfully copied unit test file to: {dest_path}")
                successful_patches += 1

            except Exception as e:
                logger.error(f"Failed to copy unit test file {src_file_path}: {str(e)}")
                failed_patches += 1

        total_patches = successful_patches + failed_patches
        if total_patches > 0:
            logger.info(
                f"Applied {successful_patches}/{total_patches} unit test patches"
            )

        return failed_patches == 0

    def to_dict(self) -> dict:
        """
        Serializes the PatchAgent state to a dictionary.
        """
        return {
            "bounty_dir": str(self.bounty_dir),
            "patch_dir": str(self.patch_dir),
            "patch_id": self.patch_id,
            "use_agent_exploit": self.use_agent_exploit,
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
