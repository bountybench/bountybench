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

    def __init__(self, task_repo_dir: str, files_dir_name: str, tmp_dir_name: str, exploit_files_dir_name: str = None, vulnerable_commit: str = None) -> None:
        # Where dir_name is a path relative to task_repo_dir, and dir is an absolut path
        self.task_repo_dir = os.path.abspath(task_repo_dir)
        self.files_dir = os.path.join(self.task_repo_dir, files_dir_name)

        self.tmp_dir_name = tmp_dir_name
        self.tmp_dir = os.path.join(self.task_repo_dir, self.tmp_dir_name)
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.resource_id = self.tmp_dir 

        self.exploit_files_dir = None
        if exploit_files_dir_name: 
            # Exploit files dir should be relative to task_repo_dir (metadata/bounty_#/exploit_files)
            self.exploit_files_dir = os.path.join(self.task_repo_dir, exploit_files_dir_name)
            self.copy_files(self.exploit_files_dir, self.tmp_dir)
        self.vulnerable_commit = vulnerable_commit
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
                f"Checking out {self.vulnerable_commit}")
            subprocess.run(
                ["git", "checkout", self.vulnerable_commit],
                cwd=self.files_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True)
            
            self.copy_files(self.files_dir, self.tmp_dir)
            git_dir = os.path.join(self.tmp_dir, ".git")

            if os.path.exists(git_dir):
                if os.path.isfile(git_dir):
                    os.remove(git_dir)
                    logger.info(f"Removed .git file from {self.tmp_dir}")
                else:
                    logger.warning(f"{git_dir} exists but is neither a directory nor a file. Skipping removal.")
                
        except subprocess.CalledProcessError as e:
            # Log error details if the script execution fails
            logger.error(f"Init script stdout: {e.stdout}")
            logger.error(f"Init script stderr: {e.stderr}")
            sys.exit(1)
        # Set up git repos

        self.setup_dev_branch(self.files_dir)
        self.setup_repo(self.tmp_dir)

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
            
            try:
                subprocess.run(["git", "branch", "-D", "dev"],
                                   cwd=self.files_dir, check=True)
                logger.info(
                        f"Removed dev branch from {self.files_dir}")
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to remove dev branch from directory: {e.stderr}")

        else:
            logger.error(f"Temporary directory does not exist: {self.tmp_dir}")

    def setup_repo(self, work_dir):
        if os.path.exists(work_dir):
            try:
                subprocess.run(["git", "init", "-q"],
                               cwd=work_dir, check=True)
                logger.info(f"Initialized git repository in {work_dir}")

                subprocess.run(["git", "branch", "-m", "main"], cwd=work_dir, check=True)
                logger.info("Branch named to main")

                subprocess.run(["git", "add", "."], cwd=work_dir, check=True)

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
                    subprocess.run(["git", "checkout", "main"],
                                   cwd=files_dir, check=True)

                    logger.info("Deleting 'dev' branch...")
                    subprocess.run(["git", "branch", "-D", "dev"],
                                   cwd=files_dir, check=True)
                    
                    subprocess.run(["git", "checkout", self.vulnerable_commit],
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