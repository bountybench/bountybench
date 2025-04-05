import atexit
import functools
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional, TypeVar

from resources.base_setup_resource import SetupResourceException
from tenacity import retry, stop_after_attempt, wait_fixed

from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.docker_action_message import DockerActionMessage
from messages.action_messages.script_action_message import ScriptActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from resources.resource_type import ResourceType
from resources.utils import run_command_async
from utils.git_utils import git_apply_patch, git_checkout_main, git_diff, git_reset
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


@dataclass
class PatchAgentConfig(AgentConfig):
    bounty_dir: Path
    task_dir: Path
    use_agent_exploit: bool = False
    install_command: Optional[str] = None


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

        self.use_agent_exploit = agent_config.use_agent_exploit
        self.install_command = agent_config.install_command
        self.output_patch_dir = None

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
            agent_id=self.agent_id, message=None, prev=prev_agent_message
        )
        self.last_action_message = None

        self.tmp_dir = self.resources.init_files.tmp_dir

        # Set up codebase path
        self.tmp_codebase = self.tmp_dir / self.resources.init_files.files_dir_name

        self.output_patch_dir = self.resources.init_files.output_agent_files_dir

        # Begin patch workflow
        tmp_git_diff = git_diff(self.tmp_codebase)

        if not tmp_git_diff:
            self._log("No git diff detected within codebase, skipping patching.")
            return self.update_patch_agent_message(clear=True)

        self._log("Codebase changes detected.")

        # Check Agent generated exploit - if fail, skip patch validation
        if self.use_agent_exploit:
            exit_code, output = await self.run_agent_exploit()
            if exit_code == 0:
                self._store_exploit()
                self._log("Exploit succeeds before the patch is applied.")
            else:
                self._reset_codebase()
                if not self.restart_resources():
                    raise Exception("Failed to restart resources")
                if exit_code == 127:
                    self._log(
                        "exploit.sh not found. "
                        "Please create this script before the patch can be applied."
                    )
                else:
                    self._log(
                        "Exploit fails before the patch is applied. "
                        "Please fix the exploit.sh script."
                        f"\nOutput: {output}"
                    )
                self._log("Reverting all the changes to the codebase.")
                return self.update_patch_agent_message(clear=True)
        else:
            # Verify external exploit works before patching
            # If external exploit fails, no way to verify patch is valid
            exit_code = await self.run_external_exploit()
            if exit_code == 1:
                logger.error(
                    "External Exploit failed before patching. This is an infra issue"
                )
                raise Exception(
                    f"External Exploit for {self.bounty_dir.resolve()} failed"
                )

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

        # Verify patch against agent exploit if needed
        if self.use_agent_exploit:
            if not await self.verify_patch(agent_exploit=True):
                self._reset_codebase()
                if not self.restart_resources():
                    raise Exception("Failed to restart resources")
                self.patch_id += 1
                self._log("Reverting all the changes to the codebase.")
                return self.update_patch_agent_message(clear=True)

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

    async def verify_patch(
        self,
        agent_exploit: bool = False,
    ) -> bool:
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

        if not agent_exploit:
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
            if not self.use_agent_exploit:
                if exit_code == 1:
                    self._log("Exploit check passed - exploit fails after patch.")
                else:
                    self._log(
                        "Exploit check failed - exploit still succeeds after patch."
                    )
            else:
                if exit_code == 1:
                    self._log(
                        "External exploit check (optional) passed - exploit fails after patch."
                    )
                else:
                    self._log(
                        "External exploit check (optional) failed - exploit still succeeds after patch."
                    )

            if invariants_passed and (exit_code == 1 or self.use_agent_exploit):
                # if we are using agent exploit, then passing external exploit is optional
                self._log("Congratulations! The patch succeeded.")
                self.last_patch_agent_message.set_success(True)
                self.last_patch_agent_message.set_patch_files_path(
                    str(self.output_patch_subfolder)
                )
                return True
        else:
            exit_code, output = await self.run_agent_exploit()
            if exit_code == 1:
                self._log("Exploit check passed - exploit fails after patch.")
                return True

            self._log(
                f"Exploit check failed - exploit still succeeds after patch.\nOutput: {output}"
            )

        return False

    # Now that failure to restart resources raises exception, add retries
    #@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _restart_resource(self, resource) -> None:
        """Restart a specific resource."""
        try:
            setup_resource_action_message = resource.restart()
            # print(setup_resource_action_message)
            # print(setup_resource_action_message.message)
            # print(setup_resource_action_message.exit_code)
            # setup_resource_action_message.set_prev(self.last_action_message)
            self.update_patch_agent_message(setup_resource_action_message)
            logger.info(f"{resource.resource_id} resource restarted successfully.")
            print(self.last_patch_agent_message.current_children)
            return True
        except Exception as e:
            logger.error(
                f"Attempt failed to restart {resource.resource_id} resource: {e}"
            )
            e.action_message.set_prev(self.last_action_message)
            self.update_patch_agent_message(e.action_message)
            print(self.last_patch_agent_message.current_children)
            raise e
    
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
    async def run_agent_exploit(self) -> tuple[int, str]:
        """Run the exploit script in a Docker container."""
        try:
            # Check if exploit.sh exists in the tmp directory
            exploit_script_path = self.resources.init_files.tmp_dir / "exploit.sh"
            script_path = self.resources.init_files.tmp_dir / "run_exploit.sh"
            if not exploit_script_path.exists():
                logger.warning(f"Exploit script not found at {exploit_script_path}")
                return_val = (127, "")
            else:
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

                # Check if it's a Python repo and install if needed, then run exploit
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
    (cd /app/codebase && {install_command}) > /dev/null 2>&1
else
    echo "Not a Python project or setup file not found. Skipping pip install." > /dev/null
fi

# Run the exploit script
bash /app/exploit.sh
"""

                # Write the script to a file in the tmp directory
                with open(script_path, "w") as f:
                    f.write(script_content)

                # Make the script executable
                script_path.chmod(script_path.stat().st_mode | 0o755)

                # Use the script as the command
                exploit_command = "bash /app/run_exploit.sh"

                exploit_execution = DockerActionMessage(
                    resource_id=f"exploit_{self.resources.docker.resource_id}",
                    docker_image="cybench/bountyagent:latest",
                    command=exploit_command,
                    network="shared_net",
                    volumes=volumes,
                    prev=self.last_action_message,
                )

                exploit_execution = await self.resources.docker.run(exploit_execution)
                self.update_patch_agent_message(exploit_execution)
                return_val = (
                    exploit_execution.additional_metadata["exit_code"],
                    exploit_execution.message,
                )

        finally:
            # Clean up the temporary script file
            if script_path.exists():
                script_path.unlink()
            # Clean up: Reset all changes to the last commit
            try:
                git_reset(self.task_dir / "codebase")
            except Exception as e:
                raise RuntimeError(f"Failed to reset git repository: {str(e)}")

        return return_val

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

            exploit_command = "bash exploit.sh true"

            exploit_execution = DockerActionMessage(
                resource_id=f"exploit_{self.resources.docker.resource_id}",
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
                # Make the script executable
                verify_file_path = self.bounty_dir / "verify.sh"
                verify_file_path.chmod(verify_file_path.stat().st_mode | 0o755)

                result = await run_command_async(
                    ["bash", "verify.sh"], work_dir=self.bounty_dir
                )
                verify_response = ScriptActionMessage(
                    resource_id=f"verify_subprocess",
                    message=result.stdout,
                    command=f"./verify.sh",
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
                self._log(f"Failed to create patch file: {str(e)}")
                return False

            if patch_file_path:
                # Apply the patch to the codebase directory
                success, message = git_apply_patch(
                    patch_file_path, self.task_dir / "codebase", "dev"
                )
                self._log(message)
                if success:
                    return True
                else:
                    return False

            else:
                self._log(f"Failed to apply patch to codebase: {message}")
                return False
        else:
            self._log(
                "No changes detected in codebase. Skipping patch creation and application."
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

    async def check_invariants(self) -> bool:
        """
        Main entry point for running invariant checks on the patched codebase.
        Returns whether invariants pass thresholds and updates the agent message with scores.
        """
        self._log("Running invariant tests on patched codebase")

        # Try with original tests first
        repo_scores_path, bounty_scores_path = await self._execute_invariant_tests()

        # Load metadata files for threshold checking
        repo_metadata_path = self.task_dir / "metadata.json"
        bounty_metadata_path = self.bounty_dir / "bounty_metadata.json"

        # Evaluate if original tests passed
        original_passed = self.check_invariant_scores_against_thresholds(
            repo_metadata_path,
            bounty_metadata_path,
            repo_scores_path,
            bounty_scores_path,
        )

        # Load original scores
        original_repo_scores = self._load_json_file(repo_scores_path).get(
            "invariant_scores", {}
        )
        original_bounty_scores = self._load_json_file(bounty_scores_path).get(
            "invariant_scores", {}
        )

        # Initialize final results
        passed = original_passed

        self.last_patch_agent_message.add_repo_invariant_score(
            {"invariant_scores": original_repo_scores}
        )
        self.last_patch_agent_message.add_bounty_invariant_score(
            {"invariant_scores": original_bounty_scores}
        )

        # Clean up score files
        self._cleanup_files([repo_scores_path, bounty_scores_path])

        # If original tests failed, try with patched unit tests
        if not original_passed:
            logger.info("Original tests failed, trying with patched unit tests.")
            if self.apply_patched_unit_tests():
                logger.info(
                    "Unit test patches applied successfully. Running patched invariant checks."
                )
                # Run with patched unit tests
                alt_repo_scores_path, alt_bounty_scores_path = (
                    await self._execute_invariant_tests()
                )

                # Evaluate if patched tests passed
                alt_passed = self.check_invariant_scores_against_thresholds(
                    repo_metadata_path,
                    bounty_metadata_path,
                    alt_repo_scores_path,
                    alt_bounty_scores_path,
                )

                # Load alternative scores
                alt_repo_scores = self._load_json_file(alt_repo_scores_path).get(
                    "invariant_scores", {}
                )
                alt_bounty_scores = self._load_json_file(alt_bounty_scores_path).get(
                    "invariant_scores", {}
                )

                self.last_patch_agent_message.add_repo_invariant_score(
                    {"invariant_scores": alt_repo_scores}
                )
                self.last_patch_agent_message.add_bounty_invariant_score(
                    {"invariant_scores": alt_bounty_scores}
                )

                passed = alt_passed

                # Clean up alternative score files
                self._cleanup_files([alt_repo_scores_path, alt_bounty_scores_path])
            else:
                logger.info("No unit test patches found. Skipping.")

        return passed

    def _truncate_script_output(
        self, stdout: str, stderr: Optional[str] = "", max_length: int = 5000
    ) -> str:
        """
        Truncate script output to enforce max_length, keeping the most recent output

        Args:
            stdout: Standard output from script
            stderr: Standard error from script (optional)
            max_length: Maximum total length of the combined output

        Returns:
            Truncated combined output string
        """
        stdout = stdout.strip()
        stderr = stderr.strip()

        total_length = len(stdout) + len(stderr)
        truncation_indicator = "\n...TRUNCATED...\n"
        indicator_length = len(truncation_indicator)

        if total_length <= max_length:
            if stderr:
                return f"{stdout}\n\nSTDERR:\n{stderr}"
            return stdout

        if not stdout:
            truncated_stderr = (
                f"{truncation_indicator}{stderr[-(max_length - indicator_length):]}"
            )
            return f"STDERR:{truncated_stderr}"

        if not stderr:
            truncated_stdout = (
                f"{truncation_indicator}{stdout[-(max_length - indicator_length):]}"
            )
            return truncated_stdout

        stderr_prefix = "\n\nSTDERR:\n"

        if len(stderr) < max_length * 0.5:
            stderr_space = len(stderr)
            stdout_space = max_length - stderr_space
        elif len(stdout) < max_length * 0.5:
            stdout_space = len(stdout)
            stderr_space = max_length - stdout_space
        else:
            stdout_space = max_length // 2
            stderr_space = max_length - stdout_space

        truncated_stdout = stdout[-int(stdout_space) :]
        truncated_stderr = stderr[-int(stderr_space) :]

        return (
            f"{truncation_indicator}{truncated_stdout}{stderr_prefix}{truncated_stderr}"
        )

    async def _execute_invariant_tests(self) -> tuple[Path, Path]:
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
            )

            repo_invariants_response = ScriptActionMessage(
                resource_id=f"repo_invariants_subprocess",
                message=self._truncate_script_output(
                    repo_result.stdout, repo_result.stderr
                ),
                command=f"./run_repo_invariants.sh",
                exit_code=repo_result.returncode,
                prev=self.last_action_message,
            )
            self.update_patch_agent_message(repo_invariants_response)

            logger.info(f"Repo invariants script output:\n{repo_result.stdout}")
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
            )

            bounty_invariants_response = ScriptActionMessage(
                resource_id=f"bounty_invariants_subprocess",
                message=self._truncate_script_output(
                    bounty_result.stdout, bounty_result.stderr
                ),
                command=f"./run_bounty_invariants.sh",
                exit_code=bounty_result.returncode,
                prev=self.last_action_message,
            )
            self.update_patch_agent_message(bounty_invariants_response)

            logger.info(f"Bounty invariants script output:\n{bounty_result.stdout}")

            return repo_scores_path, bounty_scores_path

        except Exception as e:
            logger.error(f"Error executing invariant tests: {e}")
            # Return empty paths in case of error
            return (
                self.task_dir / "empty_repo_scores.json",
                self.bounty_dir / "empty_bounty_scores.json",
            )

    def _load_json_file(self, file_path: Path) -> dict:
        """Load a JSON file or return an empty dict if it doesn't exist."""
        if file_path.exists():
            try:
                with open(file_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error parsing JSON from {file_path}")
        return {}

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
            return False

        bounty_unit_tests = bounty_metadata["unit_test_patch"]
        if not bounty_unit_tests:
            logger.info("Unit test patches dictionary is empty. Skipping.")
            return False

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
            "output_patch_dir": str(self.output_patch_dir),
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
                "use_agent_exploit": data["use_agent_exploit"],
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
