import atexit
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from resources.base_resource import BaseResource, BaseResourceConfig
from resources.utils import read_bounty_metadata
from utils.git_utils import (
    git_checkout,
    git_checkout_main,
    git_delete_branch,
    git_init_repo,
    git_setup_dev_branch,
    git_submodule_update,
)
from utils.logger import get_main_logger

# Configure logging
logger = get_main_logger(__name__)


@dataclass
class InitFilesResourceConfig(BaseResourceConfig):
    """Configuration for InitFilesResource"""

    task_dir: Path
    files_dir_name: str
    tmp_dir: Path
    bounty_number: str
    input_exploit_files_dir_name: Optional[str] = None
    input_verify_files_dir_name: Optional[str] = "verify_files"
    output_agent_files_name: Optional[str] = None
    vulnerable_commit: Optional[str] = None

    def validate(self) -> None:
        """Validate InitFiles configuration"""
        if not self.task_dir or not self.task_dir.exists():
            raise ValueError(f"Invalid task_dir: {self.task_dir}")
        if not self.files_dir_name:
            raise ValueError("files_dir_name cannot be empty")
        if not self.tmp_dir:
            raise ValueError("tmp_dir cannot be empty")


class InitFilesResource(BaseResource):
    """Init Files Resource"""

    def __init__(self, resource_id: str, config: InitFilesResourceConfig):
        super().__init__(resource_id, config)

        # Initialize from config
        self.task_dir = self._resource_config.task_dir
        self.files_dir_name = self._resource_config.files_dir_name
        self.files_dir = self.task_dir / self._resource_config.files_dir_name

        self.tmp_dir = self._resource_config.tmp_dir

        if self.tmp_dir.exists():  # clean
            logger.info(f"Removing existing {self.tmp_dir}")
            self.remove_tmp()

        # Create necessary directories
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created {self.tmp_dir}")

        # Handle exploit files if specified
        self.input_exploit_files_dir = None
        if self._resource_config.input_exploit_files_dir_name:
            self.input_exploit_files_dir = (
                self.task_dir
                / "bounties"
                / f"bounty_{self._resource_config.bounty_number}"
                / self._resource_config.input_exploit_files_dir_name
            )
            self.copy_files(self.input_exploit_files_dir, self.tmp_dir)
            self.replace_codebase_path(self.tmp_dir, self.files_dir_name)

        self.input_verify_files_dir = None
        if self._resource_config.input_verify_files_dir_name:
            self.input_verify_files_dir = (
                self.task_dir
                / "bounties"
                / f"bounty_{self._resource_config.bounty_number}"
                / self._resource_config.input_verify_files_dir_name
            )
            if (
                self.input_verify_files_dir.exists()
                and self.input_verify_files_dir.is_dir()
            ):
                self.copy_files(
                    self.input_verify_files_dir, self.tmp_dir, copy_dir=True
                )
                logger.info(
                    f"Copied verify files directory from {self.input_verify_files_dir} to {self.tmp_dir}"
                )
            else:
                logger.warning(
                    f"Verify files directory not found at {self.input_verify_files_dir}"
                )

        self.output_agent_files_dir = None
        if self._resource_config.output_agent_files_name:
            self.output_agent_files_dir = (
                self.task_dir
                / "bounties"
                / f"bounty_{self._resource_config.bounty_number}"
                / self._resource_config.output_agent_files_name
            )
            self.output_agent_files_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"Created output exploit files directory: {self.output_agent_files_dir}"
            )

        if self._resource_config.vulnerable_commit:
            self.vulnerable_commit = self._resource_config.vulnerable_commit
        else:
            self.vulnerable_commit = read_bounty_metadata(
                self.task_dir, self._resource_config.bounty_number
            )["vulnerable_commit"]

        # Initialize resource
        self._start()
        atexit.register(self.stop)

    def _start(self) -> None:
        """
        Run the initialization script for the task.
        """
        try:
            if not any(self.files_dir.iterdir()):  # If the directory is empty
                logger.info("Codebase is empty. Initializing Git submodules.")
                git_submodule_update(str(self.files_dir))

            bountyagent_dir = Path.cwd()
            logger.info("Cleaning up the working directory before checkout.")
            if (bountyagent_dir / ".git").exists():
                subprocess.run(
                    [
                        "find",
                        ".git",
                        "-type",
                        "f",
                        "-name",
                        "index.lock",
                        "-exec",
                        "rm",
                        "-f",
                        "{}",
                        ";",
                    ],
                    cwd=str(bountyagent_dir),
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    check=True,
                    text=True,
                )

            git_checkout(self.files_dir, self.vulnerable_commit, force=True)

            tmp_destination_path = self.tmp_dir / self.files_dir_name
            self.copy_files(self.files_dir, tmp_destination_path)
            git_dir = tmp_destination_path / ".git"

            if git_dir.exists():
                if git_dir.is_file():
                    git_dir.unlink()
                    logger.info(f"Removed .git file from {tmp_destination_path}")
                else:
                    logger.warning(
                        f"{git_dir} exists but is neither a directory nor a file. Skipping removal."
                    )

        except subprocess.CalledProcessError as e:
            # Log error details if the script execution fails
            logger.error(f"Init script stdout: {e.stdout}")
            logger.error(f"Init script stderr: {e.stderr}")
            raise RuntimeError(str(e))
        # Set up git repos

        git_setup_dev_branch(self.files_dir, self.vulnerable_commit)
        git_init_repo(tmp_destination_path)

    def stop(self) -> None:
        """
        Remove the temporary directory used for the task and clean up git branches.
        """
        try:
            # Clean up temporary directory
            if self.tmp_dir.exists():
                try:
                    self.remove_tmp()
                    logger.info(f"Removed temporary directory: {self.tmp_dir}")
                except Exception as e:
                    logger.error(f"Failed to remove temporary directory: {str(e)}")

            # Clean up git branches
            try:
                if self.files_dir.exists():
                    # First try to check out main branch
                    git_checkout_main(self.files_dir, force=True)
                    git_delete_branch(self.files_dir, "dev")

            except Exception as e:
                logger.error(f"Failed to clean up git branches: {str(e)}")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def remove_tmp(self):
        for item in self.tmp_dir.rglob("*"):
            self.safe_remove(item)
        self.safe_remove(self.tmp_dir)

    def safe_remove(self, path: Path):
        try:
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        except Exception as e:
            print(f"Warning: Failed to remove {path}: {e}")

    def copy_files(
        self,
        source: Path,
        destination: Path,
        copy_dir: bool = False,
    ):
        """Copy files and directories from source to destination.

        Args:
            source: Source path to copy from
            destination: Destination path to copy to
            copy_dir: Whether to copy source_dir's name
        """
        source = source.resolve()
        destination = destination.resolve()
        try:
            if source.is_file():
                shutil.copy2(source, destination)
                logger.info(f"Copied file {source} to {destination}")
            elif source.is_dir():
                # Exclude the .git folder
                if copy_dir:
                    destination = destination / source.name
                    logger.info(f"copying full directory, new dest path: {destination}")
                shutil.copytree(
                    source,
                    destination,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", ".git*"),
                )
                logger.info(f"Copied directory {source} to {destination}")
            else:
                raise ValueError(f"Source {source} is neither a file nor a directory")
        except Exception as e:
            logger.error(f"An error occurred while copying files: {e}")

    def replace_codebase_path(self, directory_path: Path, folder_to_ignore: str):
        # Walk through the directory
        for file_path in directory_path.rglob("*"):
            # If the folder to ignore is in the current directories, remove it from traversal
            if folder_to_ignore in file_path.parts:
                continue
            if file_path.is_file():
                try:
                    # Read the file content
                    content = file_path.read_text(encoding="utf-8")
                    # Replace the target string
                    new_content = content.replace("../../../codebase", "./codebase")
                    # Only write back if changes were made
                    if new_content != content:
                        file_path.write_text(new_content, encoding="utf-8")
                        print(f"Updated file: {file_path}")
                except (UnicodeDecodeError, PermissionError) as e:
                    # Skip files that cannot be read as text or have access issues
                    print(f"Skipped file: {file_path} due to {e}")

    def to_dict(self) -> dict:
        """
        Serializes the InitFilesResource state to a dictionary.
        """
        return {
            "task_dir": str(self.task_dir),
            "files_dir": str(self.files_dir),
            "tmp_dir": str(self.tmp_dir),
            "input_exploit_files_dir": (
                str(self.input_exploit_files_dir)
                if self.input_exploit_files_dir
                else None
            ),
            "input_verify_files_dir": (
                str(self.input_verify_files_dir)
                if self.input_verify_files_dir
                else None
            ),
            "output_agent_files_dir": (
                str(self.output_agent_files_dir)
                if self.output_agent_files_dir
                else None
            ),
            "vulnerable_commit": self.vulnerable_commit,
            "resource_id": self.resource_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "InitFilesResource":
        """
        Creates an InitFilesResource instance from a serialized dictionary.
        """
        return cls(
            task_dir=Path(data["task_dir"]),
            files_dir_name=Path(data["files_dir"]).name,
            input_exploit_files_dir_name=(
                Path(data["input_exploit_files_dir"]).name
                if data["input_exploit_files_dir"]
                else None
            ),
            input_verify_files_dir_name=(
                Path(data["input_verify_files_dir"]).name
                if data.get("input_verify_files_dir")
                else None
            ),
            output_agent_files_dir_name=(
                Path(data["output_agent_files_dir"]).name
                if data["output_agent_files_dir"]
                else None
            ),
            vulnerable_commit=data["vulnerable_commit"],
        )

    def save_to_file(self, filepath: Path) -> None:
        """
        Saves the resource state to a JSON file.
        """
        import json

        state = self.to_dict()
        filepath.write_text(json.dumps(state, indent=2), encoding="utf-8")

    @classmethod
    def load_from_file(cls, filepath: Path, **kwargs) -> "InitFilesResource":
        """
        Loads a resource state from a JSON file.
        """
        import json

        data = json.loads(filepath.read_text(encoding="utf-8"))
        return cls.from_dict(data, **kwargs)
