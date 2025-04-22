import atexit
import os
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
    cleanup_git_branches,
    create_git_ignore_function,
    git_checkout,
    git_checkout_main,
    git_delete_branch,
    git_init_repo,
    git_setup_dev_branch,
    git_submodule_update,
    initialize_git_repository,
    prepare_git_directory,
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
    input_verify_files_dir_name: Optional[str] = None
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
            if (
                self.input_exploit_files_dir.exists()
                and self.input_exploit_files_dir.is_dir()
            ):
                tmp_dir_exploit_files_dir = (
                    self.tmp_dir / self._resource_config.input_exploit_files_dir_name
                )
                self.copy_files(
                    self.input_exploit_files_dir,
                    self.tmp_dir,
                    copy_dir=True,
                    skip_hidden_files=True,
                )
                self.replace_codebase_path(
                    tmp_dir_exploit_files_dir, self.files_dir_name
                )
                logger.info(
                    f"Copied exploit files directory from {self.input_exploit_files_dir} to {self.tmp_dir}"
                )
            else:
                logger.warning(
                    f"Exploit files directory not found at {self.input_exploit_files_dir}"
                )

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
                    self.input_verify_files_dir,
                    self.tmp_dir,
                    copy_dir=True,
                    skip_hidden_files=True,
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
            ignore_git = False  # TODO: make this as a flag in the future
            self.copy_files(self.files_dir, tmp_destination_path, ignore_git=ignore_git)

        except subprocess.CalledProcessError as e:
            # Log error details if the script execution fails
            logger.error(f"Init script stdout: {e.stdout}")
            logger.error(f"Init script stderr: {e.stderr}")
            raise RuntimeError(str(e))
        # Set up git repos

        git_setup_dev_branch(self.files_dir, self.vulnerable_commit)
        if ignore_git:
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

    def _copy_git_directories(self, src_git_dir, dest_git_path):
        """Copy Git directories like objects, refs, hooks, and info."""
        for dir_name in ["objects", "refs", "hooks", "info"]:
            src_dir = src_git_dir / dir_name
            dst_dir = dest_git_path / dir_name
            if src_dir.exists():
                if not dst_dir.exists():
                    dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

    def _copy_git_files(self, src_git_dir, dest_git_path):
        """Copy important Git files like HEAD, description, and index."""
        for file_name in ["HEAD", "description", "index"]:
            src_file = src_git_dir / file_name
            if src_file.exists():
                shutil.copy2(src_file, dest_git_path / file_name)

    def _create_clean_git_config(self, dest_git_path):
        """Create a clean Git config file without worktree references."""
        with open(dest_git_path / "config", "w") as f:
            f.write(
                "[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n"
            )

    def _handle_git_submodule(self, git_file, source, destination):
        """Handle Git submodule reference files."""
        # Read the submodule reference
        with open(git_file, "r") as f:
            content = f.read().strip()

        if not content.startswith("gitdir:"):
            # It's a regular .git file, just copy it
            shutil.copy2(git_file, destination / ".git")
            logger.info(f"Copied .git file from {git_file} to {destination / '.git'}")
            return

        # Extract the actual Git directory path
        gitdir_path = content.split("gitdir:")[1].strip()
        if not os.path.isabs(gitdir_path):
            gitdir_path = os.path.normpath(os.path.join(source, gitdir_path))

        actual_git_dir = Path(gitdir_path)
        if not (actual_git_dir.exists() and actual_git_dir.is_dir()):
            logger.warning(
                f"Referenced Git directory {actual_git_dir} does not exist or is not a directory"
            )
            # Fall back to copying the reference file
            shutil.copy2(git_file, destination / ".git")
            return

        # Setup the destination Git repository
        dest_git_path = destination / ".git"
        prepare_git_directory(dest_git_path)

        try:
            initialize_git_repository(destination)
            self._copy_git_directories(actual_git_dir, dest_git_path)
            self._copy_git_files(actual_git_dir, dest_git_path)
            self._create_clean_git_config(dest_git_path)
            logger.info(f"Copied Git data from {actual_git_dir} to {dest_git_path}")

            # Clean up branches and make detached HEAD the new main branch
            cleanup_git_branches(destination)
            logger.info(f"Cleaned up Git branches in {destination}")
        except Exception as e:
            logger.error(f"Failed to initialize Git repository: {e}")
            # Fall back to copying the reference file
            shutil.copy2(git_file, destination / ".git")

    def _handle_git_directory(self, git_dir, destination):
        """Handle regular Git directories."""
        dest_git_path = destination / ".git"
        prepare_git_directory(dest_git_path)

        try:
            initialize_git_repository(destination)
            self._copy_git_directories(git_dir, dest_git_path)
            self._copy_git_files(git_dir, dest_git_path)
            self._create_clean_git_config(dest_git_path)
            logger.info(f"Copied Git data from {git_dir} to {dest_git_path}")

            # Clean up branches and make detached HEAD the new main branch
            cleanup_git_branches(destination)
            logger.info(f"Cleaned up Git branches in {destination}")
        except Exception as e:
            logger.error(f"Failed to initialize Git repository: {e}")

    def copy_files(
        self,
        source: Path,
        destination: Path,
        ignore_git: bool = True,
        copy_dir: bool = False,
        skip_hidden_files: bool = False,
    ):
        """Copy files and directories from source to destination.

        Args:
            source: Source path to copy from
            destination: Destination path to copy to
            ignore_git: Whether to ignore .git files and directories
            copy_dir: Whether to copy source_dir's name
            skip_hidden_files: Whether to skip all .hidden_files from copy
        """
        source = source.resolve()
        destination = destination.resolve()

        try:
            if source.is_file():
                shutil.copy2(source, destination)
                logger.info(f"Copied file {source} to {destination}")
                return

            if not source.is_dir():
                raise ValueError(f"Source {source} is neither a file nor a directory")

            if copy_dir:
                destination = destination / source.name
                logger.info(f"copying full directory, new dest path: {destination}")

            def ignore_func(directory, contents):
                ignored = []

                # For Git files - only if not already handled by skip_hidden_files
                if ignore_git and not skip_hidden_files:
                    ignored.extend(
                        [
                            item
                            for item in contents
                            if item == ".git" or item.startswith(".git/")
                        ]
                    )

                # For all dot files
                if skip_hidden_files:
                    ignored.extend([item for item in contents if item.startswith(".")])

                return ignored

            # Copy the directory structure
            shutil.copytree(
                source,
                destination,
                dirs_exist_ok=True,
                ignore=ignore_func,
            )

            # Handle Git repository if needed
            git_file = source / ".git"
            if not ignore_git and git_file.exists():
                if git_file.is_file():
                    self._handle_git_submodule(git_file, source, destination)
                elif git_file.is_dir():
                    self._handle_git_directory(git_file, destination)

            logger.info(f"Copied directory {source} to {destination}")
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
                    new_content = content.replace("../../../codebase", "../codebase")
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
