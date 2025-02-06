import atexit
import os
import subprocess
import sys
import time

from resources.base_resource import BaseResource
from resources.utils import read_bounty_metadata
from utils.logger import get_main_logger
import shutil

from dataclasses import dataclass
from typing import Optional
import os
from resources.base_resource import BaseResourceConfig


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
        self.files_dir = os.path.join(self.task_dir, self._resource_config.files_dir_name)

        self.tmp_dir_name = self._resource_config.tmp_dir_name
        self.tmp_dir = os.path.join(self.task_dir,  self.tmp_dir_name)

        if os.path.exists(self.tmp_dir): #clean
            logger.info(f"Removing existing {self.tmp_dir}")
            self.remove_tmp()

        # Create necessary directories
        os.makedirs(self.tmp_dir)
        logger.info(f"Created {self.tmp_dir}")

        # Handle exploit files if specified
        self.exploit_files_dir = self.tmp_dir
        if self._resource_config.exploit_files_dir_name:
            self.exploit_files_dir = os.path.join(
                self.task_dir, "bounties", 
                f"bounty_{self._resource_config.bounty_number}",
                self._resource_config.exploit_files_dir_name
            )
            self.copy_files(self.exploit_files_dir, self.tmp_dir)
            self.replace_codebase_path(self.tmp_dir, self.files_dir_name)
        
        if self._resource_config.vulnerable_commit:
            self.vulnerable_commit = self._resource_config.vulnerable_commit
        else: 
            self.vulnerable_commit = read_bounty_metadata(self.task_dir, self._resource_config.bounty_number)["vulnerable_commit"]
        
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
                subprocess.run(
                    ["git", "submodule", "update", "--init", "."],
                    cwd=self.files_dir,
                    stdout=sys.stdout,
                    stderr=sys.stderr, 
                    check=True,
                    text=True
                )
            logger.info("Cleaning up the working directory before checkout.")
            subprocess.run(
                ["git", "clean", "-fdx"],
                cwd=self.files_dir,
                stdout=sys.stdout,
                stderr=sys.stderr,
                check=True,
                text=True
            )
            logger.info(
                f"Checking out {self.vulnerable_commit}")
            subprocess.run(
                ["git", "checkout", self.vulnerable_commit],
                cwd=os.path.abspath(self.files_dir),
                stdout=sys.stdout, 
                stderr=sys.stderr, 
                check=True,
                text=True)
            
            tmp_destination_path = os.path.join(self.tmp_dir, self.files_dir_name)
            self.copy_files(self.files_dir, tmp_destination_path)
            git_dir = os.path.join(tmp_destination_path, ".git")

            if os.path.exists(git_dir):
                if os.path.isfile(git_dir):
                    os.remove(git_dir)
                    logger.info(f"Removed .git file from {tmp_destination_path}")
                else:
                    logger.warning(f"{git_dir} exists but is neither a directory nor a file. Skipping removal.")
                
        except subprocess.CalledProcessError as e:
            # Log error details if the script execution fails
            logger.error(f"Init script stdout: {e.stdout}")
            logger.error(f"Init script stderr: {e.stderr}")
            sys.exit(1)
        # Set up git repos

        self.setup_dev_branch(self.files_dir)
        self.setup_repo(tmp_destination_path)

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

    def setup_repo(self, work_dir):
        if os.path.exists(work_dir):
            try:
                subprocess.run(["git", "init", "-q"],
                               cwd=work_dir, check=True,
                               stdout=sys.stdout,
                               stderr=sys.stderr)
                logger.info(f"Initialized git repository in {work_dir}")

                subprocess.run(["git", "branch", "-m", "main"], cwd=work_dir, check=True, stdout=sys.stdout,
                               stderr=sys.stderr)
                logger.info("Branch named to main")

                subprocess.run(["git", "add", "."], cwd=work_dir, check=True, stdout=sys.stdout,
                               stderr=sys.stderr)

                subprocess.run(
                    ["git", "commit", "-q", "-m", "initial commit"], cwd=work_dir, check=True, stdout=sys.stdout,
                               stderr=sys.stderr)
                logger.info(f"Committed initial files in {work_dir}")
            except subprocess.CalledProcessError as e:
                logger.critical(
                    f"Failed to set up repo: {e.stderr}")
                sys.exit(1)
        else:
            logger.critical(f"Directory does not exist: {work_dir}")
            sys.exit(1)
            
    def setup_dev_branch(self, files_dir):
        try:
            # Ensure Git repository is set up
            result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                                    cwd=files_dir, 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE, 
                                    check=True, 
                                    text=True)

            if result.stdout.strip() == 'true':
                # Force checkout to the vulnerable commit
                logger.info(f"Forcing checkout to commit: {self.vulnerable_commit}")
                subprocess.run(["git", "checkout", "-f", self.vulnerable_commit],
                            cwd=files_dir, check=True,  stdout=sys.stdout,
                            stderr=sys.stderr)

                # Check if 'dev' branch exists
                branch_exists = subprocess.run(
                    ["git", "branch"], cwd=files_dir, capture_output=True, text=True
                )

                if "dev" in branch_exists.stdout:
                    logger.info("Branch 'dev' exists. Deleting it...")
                    subprocess.run(["git", "branch", "-D", "dev"],
                                cwd=files_dir, check=True,  stdout=sys.stdout,
                               stderr=sys.stderr)

                # Create and switch to a new 'dev' branch
                logger.info("Creating new 'dev' branch...")
                subprocess.run(["git", "checkout", "-b", "dev"],
                            cwd=files_dir, check=True, stdout=sys.stdout,
                            stderr=sys.stderr)
                logger.info(f"Created and switched to 'dev' branch in {files_dir}")

                # Verify the current commit
                current_commit = subprocess.run(["git", "rev-parse", "HEAD"],
                                                cwd=files_dir, capture_output=True, text=True, check=True)
                if current_commit.stdout.strip() == self.vulnerable_commit:
                    logger.info(f"Successfully checked out to commit {self.vulnerable_commit}")
                else:
                    logger.warning(f"Current commit ({current_commit.stdout.strip()}) does not match the intended vulnerable commit ({self.vulnerable_commit})")

            else:
                logger.error(f"Directory {files_dir} is not a valid git repository.")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set up 'dev' branch: {e.stderr}")
            
    def copy_files(self, source, destination):
        source = os.path.abspath(source)
        destination = os.path.abspath(destination)
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
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()

                    # Replace the target string
                    new_content = content.replace('../../../codebase', './codebase')

                    # Only write back if changes were made
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as file:
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
            'task_dir': self.task_dir,
            'files_dir': self.files_dir,
            'tmp_dir': self.tmp_dir,
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
            task_dir=data['task_dir'],
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