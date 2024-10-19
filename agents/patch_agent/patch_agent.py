import atexit
import os
import shutil
import subprocess
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

logger = get_main_logger(__name__)


class PatchAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__()
        # Check if there are TaskServerResource and InitFilesResource
        if InitFilesResource in self.resource_dict.resource_type_to_resources:
            self.init_files: InitFilesResource = self.resource_dict.get_items_of_resource_type(
                InitFilesResource)[0]
        else:
            raise RuntimeError(
                "InitFilesResource not set up. Patch agent cannot start.")

        if TaskServerResource in self.resource_dict.resource_type_to_resources:
            self.task_server: TaskServerResource = self.resource_dict.get_items_of_resource_type(
                TaskServerResource)[0]
        else:
            raise RuntimeError(
                "TaskServerResource not set up. Patch agent cannot start.")

        if DockerResource in self.resource_dict.resource_type_to_resources:
            self.docker_helper: DockerResource = self.resource_dict.get_items_of_resource_type(
                DockerResource)[0]
        else:
            raise RuntimeError(
                "DockerResource not set up. Patch agent cannot start"
            )

        self.bounty_dir = kwargs.get('bounty_dir')
        self.files_dir = os.path.join(
            self.init_files.task_repo_dir, self.init_files.files_dir)
        self.tmp_dir = os.path.join(
            self.init_files.task_repo_dir, self.init_files.tmp_dir)
        self.patch_dir = os.path.abspath(os.path.join(
            os.path.dirname(self.files_dir), "patches"))
        
        os.makedirs(self.patch_dir, exist_ok=True)


        self.patch_id = 1

    def run(self, responses: List[Response]) -> Response:
        if len(responses) != 1:
            return Exception(f'Accepts only a single response, you passed in {len(responses)} responses')
        response = responses[0]
        if issubclass(response.__class__, CommandResponseInterface):
            if self.get_git_diff(self.tmp_dir) != "":
                return self.execute(response)
            else:
                return response
        else:
            raise Exception(
                f'Response not of an interpretable type. The response type is {response.__class__} but we expect a class of CommandResponseInterface')

    def execute(self, command_response: CommandResponse) -> Response:
        """
        This function executes the patching command
        """

        tmp_dir_diff = self.get_git_diff(self.tmp_dir)
        self.create_git_patch(tmp_dir_diff, self.patch_dir)
        self.create_git_commit(self.tmp_dir)
        patch_path = os.path.abspath(os.path.join(
            self.patch_dir, f"patch_{self.patch_id}.patch"))
        self.apply_git_patch(patch_path, self.files_dir, "dev")
        self.create_git_commit(self.files_dir, "dev")


        task_server_restarted = self.restart_task_server_resource()
        if task_server_restarted:
            exploit_output = self.run_exploit()
            if self.verify_patch_works(exploit_output):
                logger.info("Exploit failed, patch succeeded.")
                return AnswerResponse(f"Answer: Congratulations! The patch succeeded.")
            else:
                logger.info("Exploit was successful, patch failed.")
        else:
            logger.error("Exploit failed after applying the patch.")
            self.git_reset(self.files_dir, "dev")
            self.git_reset(self.tmp_dir)
            command_response.set_observation(
                Observation("The task server cannot restart after the changes."))

        return command_response

    def run_exploit(self) -> str:
        """
        This function runs the exploit
        """
        volumes = {
            self.init_files.task_repo_dir: {"bind": "/app/", "mode": "rw"},
        }
        return self.docker_helper.execute(docker_image="cybench/cybounty:latest", command="./exploit.sh", network="shared_net", work_dir=os.path.join(self.bounty_dir, 'exploit_files'), volumes=volumes)

    def get_git_diff(self, directory_path: str) -> str:
        """
        This function returns the git diff of the changes in the task repository
        """
        try:
            diff = subprocess.check_output(
                ['git', 'diff'], cwd=directory_path).decode('utf-8')
            return diff
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git diff: {e}")
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
            logger.info(f"Patch_{self.patch_id} file created successfully.")
        except Exception as e:
            logger.error(
                f"Failed to create git patch_{self.patch_id} file: {e}")

    def create_git_commit(self, directory_path: str, branch_name: str = None) -> None:
        """
        This function creates a git commit
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")

            subprocess.check_call(['git', 'add', '.'], cwd=directory_path)
            subprocess.check_call(
                ['git', 'commit', '-m', f'Commit {self.patch_id}'], cwd=directory_path)
            logger.info(
                f"Commit {self.patch_id} committed successfully on branch '{branch_name}'." if branch_name else f"Commit {self.patch_id} committed successfully.")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create git commit: {e}")

    def apply_git_patch(self, patch_file: str, directory_path: str, branch_name: str = None) -> Tuple[bool, str]:
        """
        This function applies the patch file to the target directory
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")
            subprocess.check_call(
                ['git', 'apply', patch_file], cwd=directory_path)
            logger.info(
                f"Patch '{patch_file}' applied successfully on branch '{branch_name}'." if branch_name else f"Patch '{patch_file}' applied successfully.")
            return True, f"Patch '{patch_file}' applied successfully."
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply patch '{patch_file}': {e}")
            return False, f"Failed to apply patch '{patch_file}': {e}"

    def increment_patch_id(self) -> None:
        self.patch_id += 1


    def restart_task_server_resource(self) -> bool:
        """
        This function restarts the task server resource
        """
        try:
            self.task_server.restart()
            logger.info("Task server resource restarted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restart task server resource: {e}")
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
            logger.info(
                f"Git reset to HEAD~1 performed successfully on branch '{branch_name}' in {directory_path}.")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to reset git repository on branch '{branch_name}' to HEAD~1: {e}")

    def verify_patch_works(self, execution_output: str) -> bool:
        """
        Run the verify.sh script.
        """
        logger.info(f"Running verify.sh")
        result = subprocess.run(['./verify.sh', execution_output],
                                cwd=self.bounty_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Patch failed.")
            return False
        else:
            logger.info("Patch succeeded.")
            return True
        
