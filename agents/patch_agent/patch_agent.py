import atexit
import os
import shutil
import subprocess
import time
from typing import List, Tuple

from agents.base_agent import BaseAgent
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.task_server_resource import TaskServerResource
from responses.answer_response import AnswerResponse
from responses.command_response import CommandResponse
from responses.observation import Observation
from responses.command_response_interface import CommandResponseInterface
from responses.response import Response
from utils.logger import get_main_logger
from responses.patch_response import PatchResponse
import logging
import io

log_stream = io.StringIO()

def get_main_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create an in-memory stream handler
    stream_handler = logging.StreamHandler(log_stream)
    stream_handler.setLevel(logging.DEBUG)

    # Create a formatter and set it for the stream handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)

    # Add the handler to the logger
    if not logger.handlers:
        logger.addHandler(stream_handler)
    
    return logger

# Function to retrieve log history from memory
def get_logger_history():
    return log_stream.getvalue()





class PatchAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._initialize_resources()
        self.logger = get_main_logger(__name__)
        self.bounty_dir = kwargs.get('bounty_dir')
        self.patch_dir_name = "patches"
        self.patch_dir = os.path.join(self.init_files.task_repo_dir, self.patch_dir_name)
        self.exploit_files_dir_name = "exploit_files"
        self.exploit_files_dir = os.path.join(self.bounty_dir, self.exploit_files_dir_name)

        self.patch_id = 1
        os.makedirs(self.patch_dir, exist_ok=True)
        atexit.register(self.cleanup)
       
    
    def _initialize_resources(self):
        try:
            self.init_files = self._get_resource(InitFilesResource)
            self.task_server = self._get_resource(TaskServerResource)
            self.docker_helper = self._get_resource(DockerResource)
        except KeyError as e:
            raise RuntimeError(f"{e.args[0]} not set up. Patch agent cannot start.")
    
    def _get_resource(self, resource_type):
        resources = self.resource_dict.get_items_of_resource_type(resource_type)
        if not resources:
            raise KeyError(f"{resource_type.__name__}")
        return resources[0]

    def run(self, responses: List[Response]) -> Response:
        if len(responses) != 1:
            raise ValueError(f"Accepts only a single response, but received {len(responses)} responses")
        response = responses[0]
        if issubclass(response.__class__, CommandResponseInterface):
            if self.get_git_diff(self.init_files.tmp_dir):
                self.logger.info("Git diff detected, applying changes...")
                return self.execute(response)
            else: 
              self.logger.info("No git diff detected, skipping patching.")  
              return response
        else: 
            raise TypeError(f"Response not of an interpretable type. The response type is {response.__class__} but we expect a class of CommandResponseInterface")
    

    
    def execute(self, command_response: CommandResponse) -> Response:
        """
        This function executes the patching command
        """
        
        tmp_dir_diff = self.get_git_diff(self.init_files.tmp_dir)
        self.create_git_patch(tmp_dir_diff, self.patch_dir)
        self.create_git_commit(self.init_files.tmp_dir)
        patch_path = os.path.join(self.patch_dir, f"patch_{self.patch_id}.patch")
        self.apply_git_patch(patch_path, self.init_files.files_dir, "dev")
        self.create_git_commit(self.init_files.files_dir, "dev")

        task_server_restarted = self.restart_task_server_resource()
        if task_server_restarted:
            exploit_output = self.run_exploit()
            if self.verify_patch_works(exploit_output):
                self.logger.info("Exploit failed, patch succeeded.")
                return AnswerResponse(f"Answer: Congratulations! The patch succeeded.")
            else:
                self.logger.info("Exploit is successful, patch failed.")
                self.patch_id += 1
        else:
            self.logger.error("The task server cannot restart after the changes.")
            self.git_reset(self.init_files.files_dir, "dev")
            self.git_reset(self.init_files.tmp_dir)
            command_response.set_observation(
                Observation("The task server cannot restart after the changes."))

        return PatchResponse(f"{get_self.logger_history()}")

    def run_exploit(self) -> str:
        """
        This function runs the exploit
        """
        volumes = {
            self.init_files.task_repo_dir: {"bind": "/app/", "mode": "rw"}
        }
        
        exploit_command = (
            "./metadata/requirements.sh && "
            f"cd {self.exploit_files_dir} && ./exploit.sh"
        )
        
        return self.docker_helper.execute(
            docker_image="cybench/cybounty:latest",
            command=exploit_command,
            network="shared_net",
            work_dir=None,
            volumes=volumes
        )

    '''
    def get_git_diff(self, directory_path: str) -> str:
        """
        This function returns the git diff of the changes in the task repository
        """
        try:
            diff = subprocess.check_output(
                ['git', 'diff'], cwd=directory_path).decode('utf-8')
            return diff
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get git diff: {e}")
            return ""
    '''
    def get_git_diff(self, directory_path: str) -> str:
        """
        This function returns the git diff of the changes in the task repository
        and ensures the output is logged into history.
        """
        try:
            result = subprocess.run(
                ['git', 'diff'],
                cwd=directory_path,
                capture_output=True, text=True
            )
            
            # Capture stdout and stderr
            stdout = result.stdout
            stderr = result.stderr

            # Log stdout and stderr with manual addition to log stream
            if stdout:
                log_message = f"Git diff output:\n{stdout}"
                self.logger.info(log_message)
                log_stream.write(log_message + '\n')  # Add to the log history

            if stderr:
                error_message = f"Git diff errors:\n{stderr}"
                self.logger.warning(error_message)
                log_stream.write(error_message + '\n')  # Add to the log history

            return stdout
        except subprocess.CalledProcessError as e:
            error_message = f"Failed to get git diff: {e}\n{e.stdout}\n{e.stderr}"
            self.logger.error(error_message)
            log_stream.write(error_message + '\n')  # Ensure error is logged to history
            return ""
    
    def create_git_patch(self, diff: str, directory_path: str) -> None:
        """
        This function creates a patch file from the diff
        """
        try:
            patch_file_path = os.path.abspath(os.path.join(
                directory_path, f"patch_{self.patch_id}.patch"))
            with open(patch_file_path, "w") as patch_file:
                patch_file.write(diff)
            self.logger.info(f"Patch_{self.patch_id} file created successfully.")
        except Exception as e:
            self.logger.error(
                f"Failed to create git patch_{self.patch_id} file: {e}")

    def create_git_commit(self, directory_path: str, branch_name: str = None) -> None:
        """
        This function creates a git commit
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                self.logger.info(f"Checked out to branch '{branch_name}'.")

            subprocess.check_call(['git', 'add', '.'], cwd=directory_path)
            subprocess.check_call(
                ['git', 'commit', '-m', f'Commit {self.patch_id}'], cwd=directory_path)
            self.logger.info(
                f"Commit {self.patch_id} committed successfully on branch '{branch_name}'." if branch_name else f"Commit {self.patch_id} committed successfully.")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create git commit: {e}")

    def apply_git_patch(self, patch_file: str, directory_path: str, branch_name: str = None) -> Tuple[bool, str]:
        """
        This function applies the patch file to the target directory
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                self.logger.info(f"Checked out to branch '{branch_name}'.")
            subprocess.check_call(
                ['git', 'apply', patch_file], cwd=directory_path)
            self.logger.info(
                f"Patch '{patch_file}' applied successfully on branch '{branch_name}'." if branch_name else f"Patch '{patch_file}' applied successfully.")
            return True, f"Patch '{patch_file}' applied successfully."
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to apply patch '{patch_file}': {e}")
            return False, f"Failed to apply patch '{patch_file}': {e}"


    def restart_task_server_resource(self) -> bool:
        """
        This function restarts the task server resource
        """
        try:
            self.task_server.restart()
            self.logger.info("Task server resource restarted successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to restart task server resource: {e}")
            return False

    def git_reset(self, directory_path: str, branch_name: str = None) -> None:
        """
        Resets the git repository to the previous commit (HEAD~1).
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                self.logger.info(f"Checked out to branch '{branch_name}'.")
            subprocess.check_call(
                ['git', 'reset', '--hard', 'HEAD~1'], cwd=directory_path)
            self.logger.info(
                f"Git reset to HEAD~1 performed successfully in {directory_path}.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to reset git repository to HEAD~1: {e}")

    def verify_patch_works(self, execution_output: str) -> bool:
        """
        Run the verify.sh script.
        """
        self.logger.info(f"Running verify.sh")
        result = subprocess.run(['./verify.sh', execution_output],
                                cwd=os.path.join(self.init_files.task_repo_dir, self.bounty_dir), capture_output=True, text=True)
        self.logger.info(f"Verify.sh output:\n{result.stdout}")
        if result.returncode == 1:
            self.logger.info("Patch succeeded.")
            return True
        elif result.returncode == 0: # Case: exploit succeeded
            self.logger.info("Patch failed.")
            return False
        else:
            self.logger.error(f"Exit code {result.returncode} returned from verify. Patch failed.")
            return False
        
    def cleanup(self):
        self.store_patch()
        
        branch_name = "master"
        try:
            subprocess.check_call(
                ['git', 'checkout', branch_name], cwd=self.init_files.files_dir)
            self.logger.info(f"Checked out to branch '{branch_name}'.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to checkout '{branch_name}': {e}")

    def store_patch(self):
        """
        At exit, move the patches folder into a timestamped folder.
        The patches folder will act as a staging area for active patching workflows.
        The timestamped folders will store previous patch runs for future reference.
        """
        try:
            # Get the current timestamp in 'YYYYMMDD-HHMMSS' format
            timestamp = time.strftime('%Y%m%d-%H%M%S')

            # Construct the new folder name with the timestamp
            new_patch_dir = f"{self.patch_dir}-{timestamp}"

            # Ensure the patches directory exists
            if os.path.exists(self.patch_dir) and os.path.isdir(self.patch_dir):
                if os.listdir(self.patch_dir):  # Returns True if the directory has files
                    shutil.move(self.patch_dir, new_patch_dir)
                    self.logger.info(f"Patches successfully moved to {new_patch_dir}.")
                else:
                    self.logger.info("Patches directory is empty. No need to move.")
                    # Delete the old directory
                    shutil.rmtree(self.patch_dir)
            else:
                self.logger.warning(f"No patches directory found to move.")
            
        except Exception as e:
            self.logger.error(f"Failed to move patches directory: {e}")
