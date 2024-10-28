import atexit
import os
import shutil
import subprocess
import time
from typing import List, Tuple

from agents.base_agent import BaseAgent
from resources.init_files_resource import InitFilesResource
from resources.task_server_resource import TaskServerResource
from resources.docker_resource import DockerResource
from responses.answer_response import AnswerResponse
from responses.command_response import CommandResponse
from responses.observation import Observation
from responses.command_response_interface import CommandResponseInterface
from responses.response import Response
from utils.logger import get_main_logger
from responses.patch_response import PatchResponse


logger = get_main_logger(__name__)


class PatchAgent(BaseAgent):
    REQUIRED_RESOURCES = [InitFilesResource, TaskServerResource, DockerResource]
    ACCESSIBLE_RESOURCES = [InitFilesResource, TaskServerResource, DockerResource]
    
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.bounty_dir = kwargs.get('bounty_dir')
        self.patch_dir_name = "patches"
        self.patch_dir = os.path.join(self.init_files.task_repo_dir, self.patch_dir_name)
        self.exploit_files_dir_name = "exploit_files"
        self.exploit_files_dir = os.path.join(self.bounty_dir, self.exploit_files_dir_name)

        self.log_history = []
        self.patch_id = 1

        os.makedirs(self.patch_dir, exist_ok=True)
        atexit.register(self.cleanup)

    def run(self, responses: List[Response]) -> Response:
        if len(responses) != 1:
            raise ValueError(f"Accepts only a single response, but received {len(responses)} responses")
        response = responses[0]
        if issubclass(response.__class__, CommandResponseInterface):
            if self.get_git_diff(self.init_files.tmp_dir):
                logger_message = "Git diff detected, applying changes..."
                logger.info(logger_message)
                self.log_history.append(logger_message)
                execute_response =  self.execute(response)
                return execute_response
            else: 
              logger_message = "No git diff detected, skipping patching."
              logger.info(logger_message)
              self.log_history.append(logger_message)
              patch_response = PatchResponse("\n".join(self.log_history))
              self.log_history.clear()
              return patch_response
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
                logger_message = "Exploit failed, patch succeeded."
                logger.info(logger_message)
                self.log_history.append(logger_message)
                return AnswerResponse("\n".join(self.log_history) + "\nAnswer: Congratulations! The patch succeeded.")
            else:
                logger.info("Exploit is successful, patch failed.")
                self.patch_id += 1
        else:
            logger.error("The task server cannot restart after the changes.")
            self.git_reset(self.init_files.files_dir, "dev")
            self.git_reset(self.init_files.tmp_dir)
            command_response.set_observation(
                Observation("The task server cannot restart after the changes."))     
        patch_response = PatchResponse("\n".join(self.log_history))
        self.log_history.clear()
        return patch_response
        

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

    
    def get_git_diff(self, directory_path: str) -> str:
        """
        This function returns the git diff of the changes in the task repository
        """
        try:
            diff = subprocess.check_output(
                ['git', 'diff'], cwd=directory_path).decode('utf-8')
            self.log_history.append(diff)
            return diff
        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to get git diff: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)
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
            logger_message = f"Patch_{self.patch_id} file created successfully."
            logger.info(logger_message)
            self.log_history.append(logger_message)
        except Exception as e:
            logger_message = f"Failed to create git patch_{self.patch_id} file: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)

    def create_git_commit(self, directory_path: str, branch_name: str = None) -> None:
        """
        This function creates a git commit
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                logger_message = f"Checked out to branch '{branch_name}'."
                logger.info(logger_message)
                self.log_history.append(logger_message)

            subprocess.check_call(['git', 'add', '.'], cwd=directory_path)
            subprocess.check_call(
                ['git', 'commit', '-m', f'Commit {self.patch_id}'], cwd=directory_path)
            logger_message = f"Commit {self.patch_id} committed successfully on branch '{branch_name}'." if branch_name else f"Commit {self.patch_id} committed successfully."
            logger.info(logger_message)
            self.log_history.append(logger_message)

        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to create git commit: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)

    def apply_git_patch(self, patch_file: str, directory_path: str, branch_name: str = None) -> Tuple[bool, str]:
        """
        This function applies the patch file to the target directory
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                logger_message = f"Checked out to branch '{branch_name}'."
                logger.info(logger_message)
                self.log_history.append(logger_message)
            subprocess.check_call(
                ['git', 'apply', patch_file], cwd=directory_path)
            logger_message = f"Patch '{patch_file}' applied successfully on branch '{branch_name}'." if branch_name else f"Patch '{patch_file}' applied successfully."
            logger.info(logger_message)
            self.log_history.append(logger_message)
            return True, f"Patch '{patch_file}' applied successfully."
        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to apply patch '{patch_file}': {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)
            return False, f"Failed to apply patch '{patch_file}': {e}"


    def restart_task_server_resource(self) -> bool:
        """
        This function restarts the task server resource
        """
        try:
            self.task_server.restart()
            logger_message = "Task server resource restarted successfully."
            logger.info(logger_message)
            self.log_history.append(logger_message)
            return True
        except Exception as e:
            logger_message = f"Failed to restart task server resource: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)
            return False

    def git_reset(self, directory_path: str, branch_name: str = None) -> None:
        """
        Resets the git repository to the previous commit (HEAD~1).
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")
            subprocess.check_call(
                ['git', 'reset', '--hard', 'HEAD~1'], cwd=directory_path)
            logger_message =  f"Git reset to HEAD~1 performed successfully in {directory_path}."
            logger.info(logger_message)
            self.log_history.append(logger_message)
        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to reset git repository to HEAD~1: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)

    def verify_patch_works(self, execution_output: str) -> bool:
        """
        Run the verify.sh script.
        """
        logger_message = f"Running verify.sh"
        logger.info(logger_message)
        self.log_history.append(logger_message)
        result = subprocess.run(['./verify.sh', execution_output],
                                cwd=os.path.join(self.init_files.task_repo_dir, self.bounty_dir), capture_output=True, text=True)
        logger_message = f"Verify.sh output:\n{result.stdout}"
        logger.info(logger_message)
        self.log_history.append(logger_message)
        if result.returncode == 1:
            logger_message = "Patch succeeded."
            logger.info(logger_message)
            self.log_history.append(logger_message)
            return True
        elif result.returncode == 0: # Case: exploit succeeded
            logger_message = "Patch failed."
            logger.info(logger_message)
            self.log_history.append(logger_message)
            return False
        else:
            logger_message = f"Exit code {result.returncode} returned from verify. Patch failed."
            logger.error(logger_message)
            self.log_history.append(logger_message)
            return False
        
    def cleanup(self):
        self.store_patch()
        
        branch_name = "main"
        try:
            subprocess.check_call(
                ['git', 'checkout', branch_name], cwd=self.init_files.files_dir)
            logger_message = f"Checked out to branch '{branch_name}'."
            logger.info(logger_message)
            self.log_history.append(logger_message)
        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to checkout '{branch_name}': {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)


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
                    logger_message = f"Patches successfully moved to {new_patch_dir}."
                    logger.info(logger_message)
                    self.log_history.append(logger_message)
                else:
                    logger_message = "Patches directory is empty. No need to move."
                    logger.info(logger_message)
                    self.log_history.append(logger_message)
                    # Delete the old directory
                    shutil.rmtree(self.patch_dir)
            else:
                logger_message = f"No patches directory found to move."
                logger.warning(logger_message)
                self.log_history.append(logger_message)
            
        except Exception as e:
            logger_message = f"Failed to move patches directory: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)
