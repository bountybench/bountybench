import atexit
import logging
import os
import subprocess
import sys

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InitFilesResource(BaseResource):
    """Init Files Resource"""

    def __init__(self, task_repo_dir: str, files_dir: str, tmp_dir: str) -> None:
        self.resource_id = os.path.join(task_repo_dir, tmp_dir)

        self.task_repo_dir = os.path.abspath(task_repo_dir)
        self.files_dir = files_dir
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
            logger.info(
                f"Executing init script with {os.path.join(self.task_repo_dir, self.tmp_dir)}")
            subprocess.run(
                ["./init_script.sh", self.tmp_dir],
                cwd=self.task_repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            # Log error details if the script execution fails
            logger.error(f"Init script stdout: {e.stdout}")
            logger.error(f"Init script stderr: {e.stderr}")
            sys.exit(1)
        # Set up git repos
        self.setup_repo(os.path.join(self.task_repo_dir, self.files_dir))
        self.setup_dev_branch(os.path.join(self.task_repo_dir, self.files_dir))
        self.setup_repo(os.path.join(self.task_repo_dir, self.tmp_dir))

    def stop(self) -> None:
        """
        Remove the temporary directory used for the task.
        """
        tmp_dir_path = os.path.join(self.task_repo_dir, self.tmp_dir)
        if os.path.exists(tmp_dir_path):
            try:
                subprocess.run(["rm", "-rf", tmp_dir_path], check=True)
                logger.info(f"Removed temporary directory: {tmp_dir_path}")

                try:
                    local_git_dir = os.path.join(
                        self.task_repo_dir, self.files_dir, ".git")
                    if os.path.exists(local_git_dir):
                        subprocess.run(
                            ["rm", "-rf", local_git_dir], check=True)
                        logger.info(
                            f"Removed .git directory from {os.path.join(self.task_repo_dir, self.files_dir)}")
                except subprocess.CalledProcessError as e:
                    logger.error(
                        f"Failed to remove local repo directory: {e.stderr}")

            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to remove temporary directory: {e.stderr}")
        else:
            logger.error(f"Temporary directory does not exist: {tmp_dir_path}")

    def setup_repo(self, work_dir):
        if os.path.exists(work_dir):
            try:
                subprocess.run(["git", "init"],
                               cwd=work_dir, check=True)
                logger.info(f"Initialized the repository in {work_dir}")

                subprocess.run(["git", "add", "."], cwd=work_dir, check=True)
                logger.info(f"Added all files to the repository in {work_dir}")

                subprocess.run(
                    ["git", "commit", "-q", "-m", "initial commit"], cwd=work_dir, check=True)
                logger.info(f"Committed initial files in {work_dir}")
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to set up repo: {e.stderr}")
        else:
            logger.error(f"Directory does not exist: {work_dir}")

    def setup_dev_branch(self, files_dir):
        # Ensure Git repository is set up
        result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                                cwd=files_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)

        if result.stdout.strip() == 'true':
            # Create and switch to 'dev' branch
            try:
                branch_exists = subprocess.run(
                    ["git", "branch"], cwd=files_dir, capture_output=True, text=True
                )

                if "dev" in branch_exists.stdout:
                    logger.info(
                        "Branch 'dev' already exists. Switching to 'master' branch...")
                    subprocess.run(["git", "checkout", "master"],
                                   cwd=files_dir, check=True)

                    logger.info("Deleting 'dev' branch...")
                    subprocess.run(["git", "branch", "-D", "dev"],
                                   cwd=files_dir, check=True)

                subprocess.run(["git", "checkout", "-b", "dev"],
                               cwd=files_dir, check=True)
                logger.info(
                    f"Created and switched to 'dev' branch in {files_dir}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to set up 'dev' branch: {e.stderr}")
        else:
            logger.error(
                f"Directory {files_dir} is not a valid git repository.")
