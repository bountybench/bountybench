import atexit
import logging
import os
import subprocess
import sys

from resources.resource_dict import resource_dict
from resources.base_resource import BaseResource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


#things to do: 
    #Task_repo_dir: 
        # make task_repo_dir into git
        # git add .
        # git commit -m "initial commit"
        # create temporary branch
    #Temporary directory: 
        # make temporary_dir into git
        # git add .
        # git commit -m "initial commit"
        

class InitFilesResource(BaseResource):
    """Init Files Resource"""

    def __init__(self, task_repo_dir: str, tmp_dir: str) -> None:
        self.resource_id = os.path.join(task_repo_dir, tmp_dir)
        self.task_repo_dir = task_repo_dir
        self.tmp_dir = tmp_dir
        self.start()

        resource_dict[self.resource_id] = self
        atexit.register(self.stop)

    def start(self) -> None:
        """
        Run the initialization script for the task.
        """
        try:
            # Execute the init_script.sh script located in the task repo directory
            init_result = subprocess.run(
                ["./init_script.sh", self.tmp_dir],
                cwd=self.task_repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )
            # Log stdout and stderr output from the script
            logger.info(f"Init script stdout: {init_result.stdout}")
            logger.info(f"Init script stderr: {init_result.stderr}")
        except subprocess.CalledProcessError as e:
            # Log error details if the script execution fails
            logger.error(f"Init script stdout: {e.stdout}")
            logger.error(f"Init script stderr: {e.stderr}")
            sys.exit(1)

    def stop(self) -> None:
        """
        Remove the temporary directory used for the task.
        """
        tmp_dir_path = os.path.join(self.task_repo_dir, self.tmp_dir)
        if os.path.exists(tmp_dir_path):
            try:
                # Remove the temporary directory
                subprocess.run(["rm", "-rf", self.tmp_dir],
                               cwd=self.task_repo_dir, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to remove temporary directory: {e.stderr}")
        else:
            logger.error(f"Temporary directory does not exist: {tmp_dir_path}")
