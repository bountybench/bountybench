import atexit
import logging
import os
import subprocess
import sys
import time

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from utils.workflow_logger import workflow_logger
from utils.logger import get_main_logger
import shutil
from resources.configs.init_files_resource_config import InitFilesResourceConfig


# Configure logging
logger = get_main_logger(__name__)


class InitFilesResource(BaseResource):
    """Init Files Resource"""

    def __init__(self, resource_id: str, config: InitFilesResourceConfig):
        super().__init__(resource_id, config)

        self._resource_config.validate()
        
        # Initialize from config
        self.task_repo_dir = str(self._resource_config.task_repo_dir)
        self.files_dir = os.path.join(self.task_repo_dir, self._resource_config.files_dir_name)

        self.tmp_dir_name = self._resource_config.tmp_dir_name
        self.tmp_dir = os.path.join(self.task_repo_dir, self.tmp_dir_name)
        
        # Create necessary directories
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.tmp_exploits_dir = os.path.join(self.tmp_dir, "exploit_files")
        os.makedirs(self.tmp_exploits_dir, exist_ok=True)
        
        # Handle exploit files if specified
        self.exploit_files_dir = None
        if self._resource_config.exploit_files_dir_name:
            self.exploit_files_dir = os.path.join(
                self.task_repo_dir, 
                self._resource_config.exploit_files_dir_name
            )
            self.copy_files(self.exploit_files_dir, self.tmp_dir)
            
        self.vulnerable_commit = self._resource_config.vulnerable_commit
        
        # Initialize resource
        workflow_logger.add_resource(f"InitFilesResource: {self.resource_id}", self)
        self._start()
        resource_dict[self.resource_id] = self
        atexit.register(self.stop)

    def _start(self) -> None:
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
        Remove the temporary directory used for the task and clean up git branches.
        """
        try:
            # Clean up temporary directory
            if os.path.exists(self.tmp_dir):
                try:
                    shutil.rmtree(self.tmp_dir)
                    logger.info(f"Removed temporary directory: {self.tmp_dir}")
                except Exception as e:
                    logger.error(f"Failed to remove temporary directory: {str(e)}")
            
            # Clean up git branches
            try:
                if os.path.exists(self.files_dir):
                    # First try to check out main branch
                    subprocess.run(
                        ["git", "checkout", "main"],
                        cwd=self.files_dir,
                        capture_output=True,
                        check=False
                    )
                    
                    # Then try to delete the dev branch
                    subprocess.run(
                        ["git", "branch", "-D", "dev"],
                        cwd=self.files_dir,
                        capture_output=True,
                        check=False
                    )
                    logger.info(f"Removed dev branch from {self.files_dir}")
            except Exception as e:
                logger.error(f"Failed to clean up git branches: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


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
                logger.info(f"Copied file {source} to {destination}")
            elif os.path.isdir(source):
                # Exclude the .git folder 
                ignore = shutil.ignore_patterns('.git', '.git*')
                shutil.copytree(
                    source,
                    destination,
                    dirs_exist_ok=True,
                    ignore=ignore
                )
                logger.info(f"Copied directory {source} to {destination}")
            else:
                raise ValueError(f"Source {source} is neither a file nor a directory")
        except Exception as e:
            logger.error(f"An error occurred while copying files: {e}")

    def to_dict(self) -> dict:
        """
        Serializes the InitFilesResource state to a dictionary.
        """
        return {
            'task_repo_dir': self.task_repo_dir,
            'files_dir': self.files_dir,
            'tmp_dir': self.tmp_dir,
            'tmp_exploits_dir': self.tmp_exploits_dir,
            'exploit_files_dir': self.exploit_files_dir,
            'vulnerable_commit': self.vulnerable_commit,
            'resource_id': self.resource_id,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z')
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> 'InitFilesResource':
        """
        Creates an InitFilesResource instance from a serialized dictionary.
        """
        return cls(
            task_repo_dir=data['task_repo_dir'],
            files_dir_name=os.path.basename(data['files_dir']),
            exploit_files_dir_name=os.path.basename(data['exploit_files_dir']) if data['exploit_files_dir'] else None,
            vulnerable_commit=data['vulnerable_commit']
        )

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the resource state to a JSON file.
        """
        import json
        state = self.to_dict()
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, **kwargs) -> 'InitFilesResource':
        """
        Loads a resource state from a JSON file.
        """
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)