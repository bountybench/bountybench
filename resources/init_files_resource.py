import atexit
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
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

    task_dir: str
    files_dir_name: str
    tmp_dir_name: str
    bounty_number: str
    exploit_files_dir_name: Optional[str] = None
    vulnerable_commit: Optional[str] = None

    def validate(self) -> None:
        """Validate InitFiles configuration"""
        if not self.task_dir or not os.path.exists(self.task_dir):
            raise ValueError(f"Invalid task_dir: {self.task_dir}")
        if not self.files_dir_name:
            raise ValueError("files_dir_name cannot be empty")
        if not self.tmp_dir_name:
            raise ValueError("tmp_dir_name cannot be empty")
        if not self.tmp_dir_name:
            raise ValueError("tmp_dir_name cannot be empty")


class InitFilesResource(BaseResource):
    """Init Files Resource"""

    def __init__(self, resource_id: str, config: InitFilesResourceConfig):
        super().__init__(resource_id, config)

        # Initialize from config
        self.task_dir = str(self._resource_config.task_dir)
        self.files_dir_name = self._resource_config.files_dir_name
        self.files_dir = os.path.join(
            self.task_dir, self._resource_config.files_dir_name
        )

        self.tmp_dir_name = self._resource_config.tmp_dir_name
        self.tmp_dir = os.path.join(self.task_dir, self.tmp_dir_name)

        if os.path.exists(self.tmp_dir):  # clean
            logger.info(f"Removing existing {self.tmp_dir}")
            self.remove_tmp()

        # Create necessary directories
        os.makedirs(self.tmp_dir)
        logger.info(f"Created {self.tmp_dir}")

        # Handle exploit files if specified
        self.exploit_files_dir = self.tmp_dir
        if self._resource_config.exploit_files_dir_name:
            self.exploit_files_dir = os.path.join(
                self.task_dir,
                "bounties",
                f"bounty_{self._resource_config.bounty_number}",
                self._resource_config.exploit_files_dir_name,
            )
            self.copy_files(self.exploit_files_dir, self.tmp_dir)
            self.replace_codebase_path(self.tmp_dir, self.files_dir_name)

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
            if not os.listdir(self.files_dir):  # If the directory is empty
                logger.info("Codebase is empty. Initializing Git submodules.")
                git_submodule_update(self.files_dir)

            bountyagent_dir = os.getcwd()
            logger.info("Cleaning up the working directory before checkout.")
            if os.path.exists(os.path.join(bountyagent_dir, ".git")):
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
                    cwd=bountyagent_dir,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    check=True,
                    text=True,
                )

            git_checkout(self.files_dir, self.vulnerable_commit)

            tmp_destination_path = os.path.join(self.tmp_dir, self.files_dir_name)
            self.copy_files(self.files_dir, tmp_destination_path)
            git_dir = os.path.join(tmp_destination_path, ".git")

            if os.path.exists(git_dir):
                if os.path.isfile(git_dir):
                    os.remove(git_dir)
                    logger.info(f"Removed .git file from {tmp_destination_path}")
                else:
                    logger.warning(
                        f"{git_dir} exists but is neither a directory nor a file. Skipping removal."
                    )

        except subprocess.CalledProcessError as e:
            # Log error details if the script execution fails
            logger.error(f"Init script stdout: {e.stdout}")
            logger.error(f"Init script stderr: {e.stderr}")
            sys.exit(1)
        # Set up git repos

        git_setup_dev_branch(self.files_dir, self.vulnerable_commit)
        git_init_repo(tmp_destination_path)

    def stop(self) -> None:
        """
        Remove the temporary directory used for the task and clean up git branches.
        """
        try:
            # Clean up temporary directory
            if os.path.exists(self.tmp_dir):
                try:
                    self.remove_tmp()
                    logger.info(f"Removed temporary directory: {self.tmp_dir}")
                except Exception as e:
                    logger.error(f"Failed to remove temporary directory: {str(e)}")

            # Clean up git branches
            try:
                if os.path.exists(self.files_dir):
                    # First try to check out main branch
                    git_checkout_main(self.files_dir)
                    git_delete_branch(self.files_dir, "dev")

            except Exception as e:
                logger.error(f"Failed to clean up git branches: {str(e)}")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def remove_tmp(self):
        for root, dirs, files in os.walk(self.tmp_dir, topdown=False):
            for name in files:
                self.safe_remove(os.path.join(root, name))
            for name in dirs:
                self.safe_remove(os.path.join(root, name))
        self.safe_remove(self.tmp_dir)

    def safe_remove(self, path):
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"Warning: Failed to remove {path}: {e}")

    def copy_files(self, source, destination):
        source = os.path.abspath(source)
        destination = os.path.abspath(destination)
        try:
            if os.path.isfile(source):
                shutil.copy2(source, destination)
                logger.info(f"Copied file {source} to {destination}")
            elif os.path.isdir(source):
                # Exclude the .git folder
                ignore = shutil.ignore_patterns(".git", ".git*")
                shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignore)
                logger.info(f"Copied directory {source} to {destination}")
            else:
                raise ValueError(f"Source {source} is neither a file nor a directory")
        except Exception as e:
            logger.error(f"An error occurred while copying files: {e}")

    def replace_codebase_path(self, directory_path, folder_to_ignore):
        # Walk through the directory
        for root, dirs, files in os.walk(directory_path):
            # If the folder to ignore is in the current directories, remove it from traversal
            if folder_to_ignore in dirs:
                dirs.remove(folder_to_ignore)
                print(f"Excluded folder: {os.path.join(root, folder_to_ignore)}")

            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    # Read the file content
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()

                    # Replace the target string
                    new_content = content.replace("../../../codebase", "./codebase")

                    # Only write back if changes were made
                    if new_content != content:
                        with open(file_path, "w", encoding="utf-8") as file:
                            file.write(new_content)
                        print(f"Updated file: {file_path}")
                except (UnicodeDecodeError, PermissionError, IsADirectoryError) as e:
                    # Skip files that cannot be read as text or have access issues
                    print(f"Skipped file: {file_path} due to {e}")

    def to_dict(self) -> dict:
        """
        Serializes the InitFilesResource state to a dictionary.
        """
        return {
            "task_dir": self.task_dir,
            "files_dir": self.files_dir,
            "tmp_dir": self.tmp_dir,
            "exploit_files_dir": self.exploit_files_dir,
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
            task_dir=data["task_dir"],
            files_dir_name=os.path.basename(data["files_dir"]),
            exploit_files_dir_name=(
                os.path.basename(data["exploit_files_dir"])
                if data["exploit_files_dir"]
                else None
            ),
            vulnerable_commit=data["vulnerable_commit"],
        )

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the resource state to a JSON file.
        """
        import json

        state = self.to_dict()
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, **kwargs) -> "InitFilesResource":
        """
        Loads a resource state from a JSON file.
        """
        import json

        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)
