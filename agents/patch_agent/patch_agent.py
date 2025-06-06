import asyncio
import atexit
import json
import os
import shutil
import time
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_fixed

from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.docker_action_message import DockerActionMessage
from messages.action_messages.script_action_message import ScriptActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from resources.resource_type import ResourceType
from resources.utils import read_repo_metadata, run_command_async
from utils.file_utils import print_files_recursive, print_tree
from utils.git_utils import (
    git_add,
    git_apply_patch,
    git_checkout_main,
    git_diff,
    git_reset,
    git_restore,
)
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


INVARIANTS_RETRY = 3
INVARIANTS_TIMEOUT = 5400  # 90 minutes


@dataclass
class PatchAgentConfig(AgentConfig):
    bounty_dir: Path
    task_dir: Path
    submit: bool
    install_command: Optional[str] = None

    resource_restart_retry_attempts: int = 3
    resource_restart_retry_wait_seconds: int = 2


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
        self.log_history = []

        self.tmp_codebase = None
        self.tmp_dir = None
        self.output_patch_subfolder = None

        self.patch_id = 1

        self.install_command = agent_config.install_command
        self.output_patch_dir = None
        self.submit = agent_config.submit

        self.last_patch_agent_message = None
        self.last_action_message = None
        super().__init__(agent_id, agent_config)

        atexit.register(self.cleanup)

    def _log(self, message: str, level: str = "info") -> str:
        """
        Helper to append a message to log_history, log it, and return the combined log.
        Optionally clears the history after returning the combined log.
        The logging level could be adjusted (default = "info") by passing in the level string.
        """
        self.log_history.append(message)
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message, stacklevel=2)
        combined = "\n".join(self.log_history)
        return combined

    def _reset_codebase(self):
        git_reset(self.tmp_codebase)
        git_reset(self.task_dir / "codebase")

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        """Execute the main workflow of the PatchAgent."""
        # Validate input messages
        if len(messages) != 1:
            raise ValueError(
                f"Accepts only a single message, but received {len(messages)} messages"
            )

        # Initialize message state
        prev_agent_message = messages[0]
        self.last_patch_agent_message = PatchAgentMessage(
            agent_id=self.agent_id, prev=prev_agent_message
        )
        self.last_action_message = None

        self.tmp_dir = self.resources.init_files.tmp_dir

        # Set up codebase path
        self.tmp_codebase = self.tmp_dir / self.resources.init_files.files_dir_name

        self.output_patch_dir = self.resources.init_files.output_agent_files_dir

        if self.submit:
            if isinstance(prev_agent_message, ExecutorAgentMessage):
                if not prev_agent_message.submission:
                    self._log("Waiting for submission...")
                    return self.update_patch_agent_message(clear=True)

        # Begin patch workflow
        tmp_git_diff = git_diff(self.tmp_codebase)

        if not tmp_git_diff:
            self._log("No codebase changes detected")
            return self.update_patch_agent_message(clear=True)

        # Only set submision = true if codebase changes
        if self.submit and isinstance(prev_agent_message, ExecutorAgentMessage):
            self._log("Submission received.")
            self.last_patch_agent_message.set_submission(True)

        self._log("Codebase changes detected.")

        # Verify external exploit works before patching
        # If external exploit fails, no way to verify patch is valid
        exit_code = await self.run_external_exploit()
        if exit_code == 1:
            logger.error(
                "External Exploit failed before patching. This is an infra issue"
            )
            raise Exception(f"External Exploit for {self.bounty_dir.resolve()} failed")

        # Exploit / verify have side effects - restart resources
        # no codebase changes yet, so failures are infra problems
        if not self.restart_resources():
            raise Exception("Failed to restart resources")

        # Apply the patch
        _apply_patch_success = self._apply_patch(tmp_git_diff)
        if not _apply_patch_success:
            self._reset_codebase()
            # Resources haven't been changed - no need to restart
            self.patch_id += 1
            self._log("Reverting all the changes to the codebase.")
            return self.update_patch_agent_message(clear=True)

        # sanitize invariant test paths
        try:
            self.restore_invariant_test_paths()
            self._log("Successfully restored/sanitized all hidden tests in codebase.")
        except Exception as e:
            logger.error(
                "Failed to restore invariant test paths — this indicates an infrastructure issue. "
                "Sanitized test files are required for invariant checks; unsanitized files are not allowed. "
                f"Error: {e}"
            )
            raise

        # Final verification of the patch
        if not await self.verify_patch():
            self._reset_codebase()
            if not self.restart_resources():
                raise Exception("Failed to restart resources")
            self.patch_id += 1
            self._log("Reverting all the changes to the codebase.")
            return self.update_patch_agent_message(clear=True)

        # Return the final status message
        return self.update_patch_agent_message(clear=True)

    def update_patch_agent_message(
        self,
        action_message: Optional[ActionMessage] = None,
        clear: Optional[bool] = False,
    ) -> AgentMessage:
        """Update the patch agent message with the current state of the agent."""
        assert self.last_patch_agent_message

        if action_message:
            self.last_patch_agent_message.add_child_message(action_message)
            self.last_action_message = action_message

        self.last_patch_agent_message.set_message("\n".join(self.log_history))
        if clear:
            self.log_history.clear()

        return self.last_patch_agent_message

    async def verify_patch(self) -> bool:
        """Verify patch effectiveness."""

        # Failure to restart resources may be due to patch, do not raise exception
        if not self.restart_resources():
            self._log(
                "Could not restart associated resources after applying the patch. Patch is invalid."
            )
            return False

        self._log(
            "Successfully restarted associated resources after applying the patch."
        )

        invariants_passed = await self.check_invariants()
        if invariants_passed:
            self._log(
                "Hidden tests passed - all internal checks meet the required thresholds after applying the patch."
            )
        else:
            self._log(
                "Hidden tests failed - some internal checks did not meet the required thresholds after applying the patch."
            )

        exit_code = await self.run_external_exploit()
        if exit_code == 1:
            self._log("Exploit check passed - exploit fails after patch.")
        else:
            self._log("Exploit check failed - exploit still succeeds after patch.")

        if invariants_passed and exit_code == 1:
            self._log("Congratulations! The patch succeeded.")
            self.last_patch_agent_message.set_success(True)
            self.last_patch_agent_message.set_patch_files_path(
                str(self.output_patch_subfolder)
            )
            return True

        return False

    # Now that failure to restart resources raises exception, add retries
    def _restart_resource(self, resource):
        """Restart a specific resource."""
        cfg: PatchAgentConfig = self.agent_config
        retry_attempts = cfg.resource_restart_retry_attempts
        retry_wait = cfg.resource_restart_retry_wait_seconds

        @retry(stop=stop_after_attempt(retry_attempts), wait=wait_fixed(retry_wait))
        def _restart_resource_with_retry():
            try:
                resource.restart()
                logger.info(f"{resource.resource_id} resource restarted successfully.")
            except Exception as e:
                logger.error(
                    f"Attempt failed to restart {resource.resource_id} resource: {e}"
                )
                # Re-raise the exception so the @retry decorator catches it and knows to retry
                raise e

        return _restart_resource_with_retry()

    def restart_resources(self) -> bool:
        """Restart necessary resources and check success."""
        # Must restart repo_setup first, then bounty_setup (same order as initialization)
        if self.resources.has_bound(ResourceType.REPO_SETUP):
            try:
                self._restart_resource(self.resources.repo_setup)
            except Exception as e:
                logger.error(f"Failed to restart repo resource")
                return False

        if self.resources.has_bound(ResourceType.BOUNTY_SETUP):
            try:
                self._restart_resource(self.resources.bounty_setup)
            except Exception as e:
                logger.error(f"Failed to restart bounty resource")
                return False

        return True

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def run_external_exploit(self) -> Optional[int]:
        """
        Run the exploit script in a Docker container.

        Returns:
            Optional[int]: The exit code of the verify script, or None if an error occurred.
        """
        try:
            cwd = Path.cwd().resolve()
            exploit_files_path = self.bounty_dir.resolve() / "exploit_files"

            # Make the script executable
            exploit_files_path.chmod(exploit_files_path.stat().st_mode | 0o755)

            relative_path = os.path.relpath(str(exploit_files_path), str(cwd))

            volumes = {
                str(cwd): {
                    "bind": "/app",
                    "mode": "rw",
                },
            }

            exploit_command = "bash exploit.sh"

            exploit_execution = DockerActionMessage(
                resource_id=f"exploit_{self.resources.docker.resource_id}",
                docker_image="cybench/bountyagent:latest",
                command=exploit_command,
                network="shared_net",
                work_dir=f"/app/{str(relative_path)}",
                volumes=volumes,
                prev=self.last_action_message,
            )

            logger.debug(f"Printing tmp_dir before exploit")
            print_tree(self.tmp_dir)
            print_files_recursive(self.tmp_dir, self.tmp_codebase)

            exploit_execution = await self.resources.docker.run(exploit_execution)
            self.update_patch_agent_message(exploit_execution)

            logger.debug(f"Printing tmp_dir after exploit")
            print_tree(self.tmp_dir)
            print_files_recursive(self.tmp_dir, self.tmp_codebase)

            # Run the verify script
            logger.info("Running verify.sh")
            try:
                # Make the script executable
                verify_files_path = self.bounty_dir / "verify_files"
                verify_script_path = verify_files_path / "verify.sh"
                verify_script_path.chmod(verify_script_path.stat().st_mode | 0o755)

                result = await run_command_async(
                    ["bash", "verify.sh"], work_dir=verify_files_path
                )
                verify_response = ScriptActionMessage(
                    resource_id=f"verify_subprocess",
                    message=result.stdout,
                    command="bash verify.sh",
                    exit_code=result.returncode,
                    prev=self.last_action_message,
                )
                self.update_patch_agent_message(verify_response)
            except Exception as e:
                self._log(f"Error running verify.sh: {e}", level="error")
                return None

            return_val = result.returncode

        finally:
            # Clean up: Reset all changes to the last commit
            try:
                git_reset(self.task_dir / "codebase")
            except Exception as e:
                raise RuntimeError(f"Failed to reset git repository: {str(e)}") from e

        return return_val

    def _apply_patch(self, tmp_dir_diff: str) -> bool:
        """
        Apply the patch to the codebase.

        Args:
            tmp_dir_diff: The diff to apply to the codebase.

        Returns:
            bool: boolean indicating whether the patch was applied successfully
        """
        if tmp_dir_diff:
            try:
                self.output_patch_subfolder = (
                    self.output_patch_dir / f"patch_{self.patch_id}"
                )
                patch_file_path = self.create_patch_file(
                    tmp_dir_diff, self.output_patch_subfolder
                )
            except Exception as e:
                self._log(f"Failed to create patch file: {str(e)}", level="error")
                return False

            if patch_file_path:
                # Apply the patch to the codebase directory
                success, message = git_apply_patch(
                    patch_file_path, self.task_dir / "codebase", "dev"
                )
                self._log(message)
                if success:
                    # If we reach here, patch applied successfully – now stage the changes
                    # so that we can restore invariant test paths even for untracked files
                    try:
                        git_add(
                            self.task_dir / "codebase",
                            all_changes=True,
                        )  # runs `git add -A`
                        self._log("Staged patched changes successfully.")
                        return True
                    except Exception as e:
                        logger.error(
                            f"Infra issue - failed to stage patched changes: {e}"
                        )
                        raise
                else:
                    self._log(f"Failed to apply patch to codebase.")
                    return False

            else:
                self._log(f"No patch file path returned")
                return False
        else:
            self._log(
                "No changes detected in codebase. Skipping patch creation and application."
            )
            return False

    def check_invariant_scores_against_thresholds(
        self,
        repo_invariant_threshold: Dict,
        bounty_invariant_threshold: Dict,
        repo_invariant_scores: Dict,
        bounty_invariant_scores: Optional[Dict] = None,
    ) -> bool:
        """
        Check invariant scores against thresholds defined in metadata files.

        Args:
            repo_invariant_threshold: Repo invariant thresholds file
            bounty_invariant_threshold: Bounty invariant thresholds - potentially empty
            repo_invariant_scores: Repo invariant scores
            bounty_invariant_scores: Bounty invariant scores - potentially empty
        """
        try:
            if not repo_invariant_threshold:
                logger.error(
                    "Missing repo invariant thresholds - failing invariant check"
                )
                return False

            thresholds = repo_invariant_threshold.copy()
            thresholds.update(bounty_invariant_threshold)

            if not repo_invariant_scores:
                logger.error("Missing repo invariant scores - failing invariant check")
                return False

            scores = repo_invariant_scores.copy()
            if bounty_invariant_scores:
                scores.update(bounty_invariant_scores)

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

    async def check_invariants(self) -> bool:
        """
        Main entry point for running invariant checks on the patched codebase.
        Returns whether invariants pass thresholds and updates the agent message with scores.
        """
        self._log("Running invariant tests on patched codebase")

        repo_invariant_threshold = {}
        bounty_invariant_threshold = {}

        # Load metadata files for threshold checking
        repo_metadata_path = self.task_dir / "metadata.json"
        bounty_metadata_path = self.bounty_dir / "bounty_metadata.json"

        if repo_metadata_path.exists():
            repo_metadata = json.loads(repo_metadata_path.read_text())
            repo_invariant_threshold = repo_metadata.get(
                "invariant_thresholds", {}
            ).copy()

        if bounty_metadata_path.exists():
            bounty_metadata = json.loads(bounty_metadata_path.read_text())
            bounty_invariant_threshold = bounty_metadata.get(
                "invariant_thresholds", {}
            ).copy()

        any_passed = False

        for attempt in range(INVARIANTS_RETRY):
            self._log(f"Attempt {attempt + 1} of {INVARIANTS_RETRY}")

            try:
                original_repo_scores, original_bounty_scores = (
                    await self._execute_invariant_tests()
                )
            except asyncio.TimeoutError:
                self._log(
                    f"Invariant test attempt {attempt + 1} timed out after {INVARIANTS_TIMEOUT//60} minutes ({INVARIANTS_TIMEOUT} seconds).",
                    level="error",
                )
                continue

            # Evaluate if tests passed
            original_passed = self.check_invariant_scores_against_thresholds(
                repo_invariant_threshold,
                bounty_invariant_threshold,
                original_repo_scores,
                original_bounty_scores,
            )

            # Update any_passed if this attempt succeeded
            if original_passed:
                any_passed = True

        return any_passed

    async def _execute_invariant_tests(self) -> tuple[Dict]:
        """
        Execute invariant test scripts.
        Returns paths to the generated score files.
        """
        try:
            logger.info(f"Executing invariant tests for {self.task_dir.name}")

            # Define paths to score files
            repo_scores_path = self.task_dir / "invariant_scores.json"
            bounty_scores_path = self.bounty_dir / "invariant_scores.json"

            # Make the script executable
            repo_invariants_file_path = self.task_dir / "run_repo_invariants.sh"
            repo_invariants_file_path.chmod(
                repo_invariants_file_path.stat().st_mode | 0o755
            )

            # Run repo invariants script
            logger.info("Running repo invariants script")
            repo_result = await run_command_async(
                ["bash", "run_repo_invariants.sh"],
                work_dir=self.task_dir,
                timeout=INVARIANTS_TIMEOUT,
            )

            repo_scores = self._load_json_file(repo_scores_path).get(
                "invariant_scores", {}
            )
            repo_scores_str = self._score_to_str(repo_scores)
            logger.info(f"Repo invariants check scores:\n{repo_scores_str}")
            self._cleanup_files([repo_scores_path])

            repo_invariants_response = ScriptActionMessage(
                resource_id=f"repo_invariants_subprocess",
                message=f"{repo_result.stdout}\n{repo_result.stderr}\nRepo invariants check scores:\n{repo_scores_str}",
                command="bash run_repo_invariants.sh",
                exit_code=repo_result.returncode,
                additional_metadata={"repo_invariant_scores": repo_scores},
                prev=self.last_action_message,
            )
            self.update_patch_agent_message(repo_invariants_response)

            logger.info(f"Repo invariants script output:\n{repo_result.stdout}")
            if repo_result.stderr:
                logger.info(f"Repo invariants script stderr:\n{repo_result.stderr}")

            # Make the script executable
            bounty_invariants_file_path = self.bounty_dir / "run_bounty_invariants.sh"
            bounty_invariants_file_path.chmod(
                bounty_invariants_file_path.stat().st_mode | 0o755
            )

            # Run bounty invariants script
            logger.info("Running bounty invariants script")
            bounty_result = await run_command_async(
                ["bash", "run_bounty_invariants.sh"],
                work_dir=self.bounty_dir,
                timeout=INVARIANTS_TIMEOUT,
            )

            bounty_scores = self._load_json_file(bounty_scores_path).get(
                "invariant_scores", {}
            )
            bounty_scores_str = self._score_to_str(bounty_scores)
            logger.info(f"Bounty invariants check scores:\n{bounty_scores_str}")
            self._cleanup_files([bounty_scores_path])

            bounty_invariants_response = ScriptActionMessage(
                resource_id=f"bounty_invariants_subprocess",
                message=f"{bounty_result.stdout}\n{bounty_result.stderr}\nBounty invariants check scores:\n{bounty_scores_str}",
                command="bash run_bounty_invariants.sh",
                exit_code=bounty_result.returncode,
                additional_metadata={"bounty_invariant_scores": bounty_scores},
                prev=self.last_action_message,
            )
            self.update_patch_agent_message(bounty_invariants_response)

            logger.info(f"Bounty invariants script output:\n{bounty_result.stdout}")
            if bounty_result.stderr:
                logger.info(f"Bounty invariants script stderr:\n{bounty_result.stderr}")

            return repo_scores, bounty_scores

        except Exception as e:
            logger.error(f"Error executing invariant tests: {e}")
            # Return empty dicts in case of error
            return {}, {}

    def _load_json_file(self, file_path: Path) -> dict:
        """Load a JSON file or return an empty dict if it doesn't exist."""
        if file_path.exists():
            try:
                with open(file_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error parsing JSON from {file_path}")
        return {}

    def _score_to_str(self, score: dict) -> str:
        """Convert a dictionary of scores into a formatted string."""
        if not score:
            return "No scores available"

        result = []
        for check, value in score.items():
            result.append(f"{check}: {value}")
        return "\n".join(result)

    def _cleanup_files(self, file_paths: List[Path]) -> None:
        """Delete files if they exist."""
        for path in file_paths:
            if path.exists():
                path.unlink()
                logger.info(f"Removed {path.name}")

    def create_patch_file(self, diff: str, directory_path: Path) -> Optional[Path]:
        """
        Create a patch file at directory_path using the provided diff.

        Example:
            tmp_dir_diff = git_diff(self.tmp_codebase)
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

        self._store_exploit()
        if self.tmp_codebase and self.tmp_codebase.exists():
            git_checkout_main(self.tmp_codebase, force=True)

    def _store_exploit(self) -> Optional[str]:
        """Store the exploit files."""
        try:
            if self.output_patch_dir is None:
                return None

            self.output_patch_subfolder = (
                self.output_patch_dir / f"patch_{self.patch_id}"
            )
            if self.tmp_dir.exists() and self.tmp_dir.is_dir():
                if any(self.tmp_dir.iterdir()):
                    shutil.copytree(
                        self.tmp_dir,
                        self.output_patch_subfolder,
                        ignore=shutil.ignore_patterns("codebase"),
                    )
                    logger.info(
                        f"Exploits successfully moved to corresponding patch directory {self.output_patch_subfolder}."
                    )
                    return str(self.output_patch_subfolder)
                else:
                    logger.warning("Exploits directory is empty. No files to move.")
            else:
                logger.warning("No exploits directory found to move.")
        except Exception as e:
            logger.error(f"Failed to move exploits directory: {e}")

        return None

    def restore_invariant_test_paths(self) -> None:
        """Restore invariant test paths specified in repo and bounty metadata."""
        repo_meta = read_repo_metadata(self.task_dir)
        paths_to_restore = repo_meta.get("invariant_test_paths", [])

        if not paths_to_restore:
            logger.info("No invariant test paths found in repo metadata.")
            return

        total_restores = len(paths_to_restore)
        successes = 0

        for path in paths_to_restore:
            logger.info(f"Restoring invariant test path: {path}")
            try:
                relative_path = Path(path).relative_to(
                    "codebase"
                )  # checks whether first part is "codebase"
                codebase_root = self.task_dir / "codebase"
                git_restore(
                    codebase_root,
                    paths=[codebase_root / relative_path],
                    staged=True,
                    worktree=True,
                )
                logger.info(f"✔ Successfully restored: {path}")
                successes += 1
            except Exception as e:
                logger.error(f"✖ Failed to restore {path}: {e}")

        logger.info(f"Restored {successes}/{total_restores} invariant test paths.")
        if successes < total_restores:
            logger.error("Failed to restore all invariant test paths.")
            failed_count = total_restores - successes
            raise RuntimeError(
                f"Only {successes}/{total_restores} invariant test paths were restored "
                f"({failed_count} failed); see log entries for details."
            )

    def to_dict(self) -> dict:
        """
        Serializes the PatchAgent state to a dictionary.
        """
        return {
            "bounty_dir": str(self.bounty_dir),
            "output_patch_dir": str(self.output_patch_dir),
            "patch_id": self.patch_id,
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
            }
        )

        agent = cls(**kwargs)
        agent.output_patch_dir = Path(data["output_patch_dir"])
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
