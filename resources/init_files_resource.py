import atexit
import logging
import os
import subprocess
import sys

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from utils.logger import get_main_logger
import shutil


# Configure logging
logger = get_main_logger(__name__)


class InitFilesResource(BaseResource):
    """Init Files Resource"""

    def __init__(self, task_repo_dir: str, files_dir_name: str, tmp_dir_name: str, vulnerable_commit: str = None) -> None:
        # Where dir_name is a path relative to task_repo_dir, and dir is an absolut path
        self.task_repo_dir = os.path.abspath(task_repo_dir)
        self.files_dir = os.path.join(self.task_repo_dir, files_dir_name)

        self.tmp_dir_name = tmp_dir_name
        self.tmp_dir = os.path.join(self.task_repo_dir, self.tmp_dir_name)
        self.resource_id = self.tmp_dir 
        self.vulnerable_commit = vulnerable_commit

        self.start()

        resource_dict[self.resource_id] = self
        atexit.register(self.stop)

    def start(self) -> None:
   
        
        try:
            # Execute the init_script.sh script located in the task repo directory
            logger.info(
                f"Checking out {self.vulnerable_commit}")
            subprocess.run(
                ["git", "checkout", self.vulnerable_commit],
                cwd=self.files_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )
            self.copy_files(self.files_dir, self.tmp_dir)
        except subprocess.CalledProcessError as e:
            # Log error details if the script execution fails
            logger.error(f"Init script stdout: {e.stdout}")
            logger.error(f"Init script stderr: {e.stderr}")
            sys.exit(1)

    def stop(self) -> None:
        """
        Remove the temporary directory used for the task.
        """
        if os.path.exists(self.tmp_dir):
            try:
                subprocess.run(["rm", "-rf", self.tmp_dir], check=True)
                logger.info(f"Removed temporary directory: {self.tmp_dir}")

            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to remove temporary directory: {e.stderr}")
        else:
            logger.error(f"Temporary directory does not exist: {self.tmp_dir}")

    def copy_files(self, source, destination): 
        try:
            if os.path.isfile(source):
                shutil.copy2(source, destination)
                print(f"Copied file {source} to {destination}")
            elif os.path.isdir(source):
                shutil.copytree(source, destination, dirs_exist_ok=True)
                print(f"Copied directory {source} to {destination}")
            else:
                raise ValueError(f"Source {source} is neither a file nor a directory")
        except Exception as e:
                print(f"An error occurred while copying files: {e}")