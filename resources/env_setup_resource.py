import os
import subprocess
import sys
import atexit

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from utils.logger import get_main_logger


# Configure logging
logger = get_main_logger(__name__)


class EnvSetupResource(BaseResource):

    def __init__(self, task_repo_dir: str, files_dir_name: str) -> None:
        self.task_repo_dir = os.path.abspath(task_repo_dir)
        self.files_dir = os.path.join(self.task_repo_dir, files_dir_name)

        self.resource_id = self.task_repo_dir 

        self._start()

        resource_dict[self.resource_id] = self
        atexit.register(self.stop)

    def _start(self) -> None:
        """
        Run the repository setup script to create the original_files dir.
        """
        try:
            logger.info("Running repo setup script to create repository directory.")
            subprocess.run(
                ["./repo_setup.sh", self.files_dir],
                cwd=self.task_repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )
            logger.info(f"Repository directory created at {self.files_dir}.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Repo setup stdout: {e.stdout}")
            logger.error(f"Repo setup stderr: {e.stderr}")
            sys.exit(1)

        if not os.path.exists(self.files_dir):
            logger.error(f"Failed to create repo folder at {self.files_dir}.")
            sys.exit(1)


    def stop(self) -> None:
        """
        Remove the cloned repo used for the task.
        """
        if os.path.exists(self.task_repo_dir):
            try:
                subprocess.run(["rm", "-rf", self.files_dir], check=True)
                logger.info(f"Removed cloned repository directory: {self.files_dir}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to remove repository directory: {e.stderr}")
        else:
            logger.warning(f"Repository directory does not exist: {self.files_dir}")

   